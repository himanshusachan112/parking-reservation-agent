# ============================================
# ParkSmart — Deployment Guide
# ============================================
# Complete instructions for deploying the AI Parking Reservation Platform.
# Covers Docker, Render, Vercel, CI/CD, and Terraform.
# ============================================

## Table of Contents

1. [Quick Start with Docker](#docker-deployment)
2. [CI/CD with GitHub Actions](#cicd-setup)
3. [Production Deployment](#production-deployment)
4. [Terraform Infrastructure](#terraform-usage)
5. [Environment Variables](#environment-variables)
6. [Production Checklist](#production-checklist)

---

## Docker Deployment

### Prerequisites
- Docker Engine 24+ and Docker Compose v2
- `.env` file with required variables (copy from `.env.example`)

### Build & Run

```bash
# Build and start all services
docker compose up --build

# Run in background
docker compose up -d --build

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Stop services
docker compose down

# Full cleanup (removes volumes)
docker compose down -v
```

### Health Checks

```bash
# Simple health check
curl http://localhost:8000/api/health

# Detailed health check (DB, vector DB, email status)
curl http://localhost:8000/api/health/detailed

# Frontend
curl http://localhost:3000
```

### Individual Images

```bash
# Build backend only
docker build -t parksmart-backend .

# Build frontend only
docker build -t parksmart-frontend ./frontend \
  --build-arg NEXT_PUBLIC_API_URL=http://your-backend-url:8000

# Run backend
docker run -p 8000:8000 --env-file .env parksmart-backend

# Run frontend
docker run -p 3000:3000 parksmart-frontend
```

---

## CI/CD Setup

### GitHub Actions Workflows

| Workflow | File | Triggers On |
|----------|------|-------------|
| Backend CI | `.github/workflows/backend-ci.yml` | Push/PR to `src/`, `tests/`, `config/`, `requirements.txt` |
| Frontend CI | `.github/workflows/frontend-ci.yml` | Push/PR to `frontend/` |
| Docker Build | `.github/workflows/docker-build.yml` | Push/PR to Docker-related files |

### Backend CI Pipeline
1. **Lint & Format**: Black, isort, flake8, mypy
2. **Test Suite**: pytest with coverage report
3. **Startup Validation**: Imports FastAPI app, hits `/api/health`

### Frontend CI Pipeline
1. **Lint**: ESLint + TypeScript type checking
2. **Build**: Production Next.js build

### Docker Pipeline
1. **Build**: Backend and frontend Docker images
2. **Validate**: docker-compose config syntax
3. **Integration**: Starts services, runs health checks

### Setup Steps
1. Push code to GitHub
2. Workflows run automatically on push/PR
3. No secrets needed for testing (uses mock API keys)
4. Add deployment secrets for production pushes

---

## Production Deployment

### Backend on Render

1. **Create Render account**: https://render.com
2. **New Web Service** → Connect your GitHub repo
3. **Configure**:
   - **Build Command**: `pip install -r requirements.txt && python -m spacy download en_core_web_lg && python main.py --setup`
   - **Start Command**: `uvicorn src.api.server:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/api/health`
4. **Environment Variables** → Add all from `.env.example`
5. **Deploy**

### Frontend on Vercel

1. **Install Vercel CLI**: `npm i -g vercel`
2. **Deploy**:
   ```bash
   cd frontend
   vercel --prod
   ```
3. **Set Environment Variable**:
   - `NEXT_PUBLIC_API_URL` = your Render backend URL (e.g., `https://parksmart-api.onrender.com`)
4. **Redeploy** after setting env vars:
   ```bash
   vercel --prod
   ```

### Update CORS

After deploying, update `src/api/server.py` CORS origins to include your Vercel domain:

```python
allow_origins=[
    "http://localhost:3000",
    "https://your-app.vercel.app",
],
```

---

## Terraform Usage

### Prerequisites
- Terraform >= 1.5 installed
- Render API key
- Vercel API token (optional)

### Deploy Infrastructure

```bash
cd terraform

# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Apply (creates resources)
terraform apply

# Destroy (removes all resources)
terraform destroy
```

### Configuration

Create `terraform/terraform.tfvars`:

```hcl
render_api_key   = "your-render-api-key"
dial_api_key     = "your-dial-api-key"
pinecone_api_key = "your-pinecone-api-key"
smtp_host        = "smtp.gmail.com"
smtp_port        = 465
smtp_username    = "your-email@gmail.com"
smtp_password    = "your-app-password"
admin_email      = "admin@yourcompany.com"
```

> **NEVER** commit `terraform.tfvars` to git — it contains secrets.

---

## Environment Variables

### Backend (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `DIAL_API_KEY` | Yes | EPAM DIAL / Azure OpenAI API key |
| `PINECONE_API_KEY` | Yes | Pinecone vector database API key |
| `PINECONE_INDEX_NAME` | No | Pinecone index name (default: `parking-info`) |
| `PINECONE_ENVIRONMENT` | No | Pinecone region (default: `us-east-1`) |
| `SMTP_HOST` | No | SMTP server (default: none → console fallback) |
| `SMTP_PORT` | No | SMTP port (default: `465`) |
| `SMTP_USERNAME` | No | SMTP login username |
| `SMTP_PASSWORD` | No | SMTP app-specific password |
| `ADMIN_EMAIL` | No | Admin notification email |
| `SQL_DATABASE_URL` | No | SQLite URL (default: `sqlite:///./data/parking_dynamic.db`) |

### Frontend (`.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Yes | Backend API base URL (default: `http://localhost:8000`) |

### Security Notes

- **Never commit** `.env`, `.env.local`, or `terraform.tfvars`
- Use **app-specific passwords** for Gmail SMTP (not your real password)
- Rotate API keys regularly
- Use GitHub Secrets for CI/CD pipeline variables

---

## Production Checklist

### Pre-Deployment
- [ ] All tests pass (`python -m pytest`)
- [ ] Frontend builds cleanly (`cd frontend && npm run build`)
- [ ] Code linting passes (`black --check . && isort --check-only . && flake8`)
- [ ] `.env.example` is up to date
- [ ] No secrets in committed code (`git log --all -p | grep -i "api_key\|password"`)

### Infrastructure
- [ ] Docker images build successfully
- [ ] `docker compose up` starts both services
- [ ] Health checks pass (`/api/health`, `/api/health/detailed`)
- [ ] CORS origins include production frontend URL

### Security
- [ ] Non-root Docker containers
- [ ] Environment variables for all secrets (no hardcoded values)
- [ ] `.gitignore` includes `.env`, `terraform.tfvars`, `logs/`
- [ ] PII guardrails enabled (`GUARDRAILS_ENABLED=true`)
- [ ] Admin portal protected by authentication gate

### Monitoring
- [ ] Structured logging configured (`src/utils/logging_config.py`)
- [ ] Log rotation enabled (5 MB × 5 backups)
- [ ] Health check endpoints respond correctly
- [ ] Error logs separated from application logs
