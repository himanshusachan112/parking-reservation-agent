<!-- markdownlint-disable MD033 MD041 -->
<div align="center">

# 🚗 ParkSmart — AI Parking Reservation Platform

[![Backend CI](https://github.com/sanyam991/parking-chatbot/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/sanyam991/parking-chatbot/actions/workflows/backend-ci.yml)
[![Frontend CI](https://github.com/sanyam991/parking-chatbot/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/sanyam991/parking-chatbot/actions/workflows/frontend-ci.yml)
[![Docker Build](https://github.com/sanyam991/parking-chatbot/actions/workflows/docker-build.yml/badge.svg)](https://github.com/sanyam991/parking-chatbot/actions/workflows/docker-build.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-209%20passing-brightgreen.svg)](#-testing)

**An enterprise-grade AI-powered parking reservation system with RAG, LangGraph orchestration, human-in-the-loop admin approval, and a modern React frontend.**

[Quick Start](#-installation) · [Architecture](#-solution-architecture) · [API Docs](#-api-endpoints) · [Demo](#-demo-access) · [Deployment](#-deployment-guide)

</div>

---

## 📋 Table of Contents

1. [Project Overview](#-project-overview)
2. [Problem Statement](#-problem-statement)
3. [Solution Architecture](#-solution-architecture)
4. [Key Features](#-key-features)
5. [System Workflow](#-system-workflow)
6. [LangGraph Orchestration](#-langgraph-orchestration-flow)
7. [Tech Stack](#-tech-stack)
8. [Frontend Architecture](#-frontend-architecture)
9. [Backend Architecture](#-backend-architecture)
10. [Vector Database (Pinecone)](#-vector-database--pinecone)
11. [RAG Pipeline](#-rag-pipeline)
12. [Human-in-the-Loop Workflow](#-human-in-the-loop-workflow)
13. [SMTP Notification Workflow](#-smtp-notification-workflow)
14. [Admin Dashboard](#-admin-dashboard)
15. [Security Features](#-security-features)
16. [Docker Setup](#-docker-setup)
17. [CI/CD Pipeline](#-cicd-pipeline)
18. [Terraform Infrastructure](#-terraform-infrastructure)
19. [API Endpoints](#-api-endpoints)
20. [Installation](#-installation)
21. [Local Development](#-local-development)
22. [Environment Variables](#-environment-variables)
23. [Testing](#-testing)
24. [Deployment Guide](#-deployment-guide)
25. [Screenshots](#-screenshots)
26. [Demo Access](#-demo-access)
27. [Future Enhancements](#-future-enhancements)
28. [Contributors](#-contributors)
29. [License](#-license)

---

## 📖 Project Overview

ParkSmart is a production-ready AI parking reservation chatbot that combines **Retrieval-Augmented Generation (RAG)** with a **LangGraph state-machine pipeline** to deliver a complete reservation lifecycle — from natural-language Q&A through booking, admin review, email notification, and file-based record keeping.

The platform was developed iteratively across **four stages**, each adding a major architectural layer:

| Stage | Capability | Tests Added |
|-------|-----------|-------------|
| **Stage 1** | RAG Chatbot + Guardrails + Evaluation | 35 |
| **Stage 2** | REST API + Admin Agent + Email Notifications | 44 |
| **Stage 3** | MCP Tool Server + Client + Fallback | 21 |
| **Stage 4** | LangGraph Orchestration + Frontend + DevOps | 61 |
| **Total** | **Full-stack AI platform** | **161** |

---

## 🎯 Problem Statement

Traditional parking management relies on manual phone/email booking, lacks real-time availability checks, and offers no intelligent Q&A. Administrators juggle spreadsheets, and users have no self-service portal.

**Challenges addressed:**

- No natural-language interface for parking inquiries
- Manual, error-prone reservation workflows
- No admin approval pipeline with audit trail
- Lack of automated notifications to users and admins
- No unified orchestration — operators run separate scripts

---

## 🏗 Solution Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js 16)                        │
│   ┌──────────┐  ┌──────────────┐  ┌───────────────┐               │
│   │ Chat UI  │  │ Admin Portal │  │ Theme/Layout  │               │
│   │ (Zustand)│  │ (Dashboard)  │  │ (shadcn/ui)   │               │
│   └────┬─────┘  └──────┬───────┘  └───────────────┘               │
└────────┼────────────────┼──────────────────────────────────────────┘
         │  HTTP/REST     │
┌────────▼────────────────▼──────────────────────────────────────────┐
│                     BACKEND (FastAPI :8000)                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                   GUARDRAILS LAYER                            │  │
│  │         Prompt injection detection + PII redaction            │  │
│  └──────────────────────┬───────────────────────────────────────┘  │
│  ┌──────────────────────▼───────────────────────────────────────┐  │
│  │                   LANGGRAPH PIPELINE                          │  │
│  │  user_interaction → save → admin_review → notify → mcp → end │  │
│  └──────────────────────┬───────────────────────────────────────┘  │
│  ┌──────────┐  ┌────────▼────────┐  ┌────────────┐  ┌──────────┐ │
│  │ RAG Chain│  │  SQL Database   │  │Email Service│  │MCP Client│ │
│  │(LangChain│  │   (SQLite /     │  │  (SMTP)     │  │(HTTP)    │ │
│  │+Pinecone)│  │  SQLAlchemy)    │  │             │  │          │ │
│  └──────────┘  └─────────────────┘  └─────────────┘  └────┬─────┘ │
└────────────────────────────────────────────────────────────┼───────┘
                                                             │
┌────────────────────────────────────────────────────────────▼───────┐
│                      MCP SERVER (FastAPI :8001)                     │
│         Tool discovery + execution + file-based storage             │
└───────────────────────────────────────────────────────────────────┘
```

---

## ✨ Key Features

| Category | Feature | Description |
|----------|---------|-------------|
| **AI/NLP** | RAG Q&A | Retrieval-augmented answers from Pinecone vector DB |
| **AI/NLP** | Guardrails | Prompt injection detection + PII redaction (Presidio) |
| **Booking** | Interactive Reservation | Step-by-step data collection via chatbot |
| **Booking** | Admin Approval | Human-in-the-loop review with approve/reject |
| **Notify** | Email Notifications | SMTP SSL/STARTTLS with HTML templates + retry |
| **Infra** | LangGraph Orchestration | 6-node state graph with conditional routing |
| **Infra** | MCP Tool Server | Model Context Protocol for reservation file storage |
| **Frontend** | Next.js Chat UI | Real-time chat with session management (Zustand) |
| **Frontend** | Admin Dashboard | Reservation list, approve/reject, status filters |
| **DevOps** | Docker Compose | Multi-stage builds, health checks, non-root user |
| **DevOps** | GitHub Actions CI/CD | 3 workflows — backend, frontend, Docker/Terraform |
| **DevOps** | Terraform IaC | Render backend + Vercel frontend templates |

---

## 🔄 System Workflow

```
User opens chat → Asks question or starts booking
        │
        ▼
   ┌─────────────┐     ┌──────────────┐
   │ RAG Q&A?    │─Yes─▶│ Vector search │──▶ LLM response ──▶ User
   └──────┬──────┘     └──────────────┘
          │ No (booking)
          ▼
   Collect: name → email → car → type → start → end
          │
          ▼
   Confirm with user → Save to SQLite (status: pending)
          │
          ▼
   Email admin notification → Admin reviews in dashboard
          │
     ┌────┴────┐
     ▼         ▼
  Approve    Reject
     │         │
     ▼         ▼
  Update DB  Update DB
     │         │
     ▼         ▼
  Email user Email user
     │         │
     ▼         │
  MCP record   │
     │         │
     └────┬────┘
          ▼
      Complete
```

---

## 🔗 LangGraph Orchestration Flow

The entire reservation lifecycle is managed by a **LangGraph StateGraph** with 6 nodes and 3 conditional edge functions:

```
                    ┌──────────────────┐
                    │ user_interaction  │ ◀── Entry point
                    └────────┬─────────┘
                             │
                    booking complete?
                    ├── No ──▶ END (return Q&A response)
                    └── Yes
                    ┌────────▼─────────┐
                    │ save_reservation  │
                    └────────┬─────────┘
                    ┌────────▼─────────┐
                    │  admin_review     │ ◀── Human-in-the-loop
                    └───┬──────────┬───┘
                        │          │
                    approve     reject
                        │          │
                    ┌───▼──┐   ┌──▼───┐
                    │notify│   │notify │
                    └───┬──┘   └──┬───┘
                        │          │
                    ┌───▼──┐       │
                    │ MCP  │       │
                    └───┬──┘       │
                    ┌───▼──────────▼───┐
                    │    completion     │
                    └──────────────────┘
```

**GraphState** — a `TypedDict` with 14 fields — flows through every node. Each node reads relevant fields, performs its work, and returns only the fields it changed. LangGraph merges updates automatically.

<p align="center">
  <img src="Screenshots/langgraph_workflow.png" alt="LangGraph Workflow" width="80%">
  <br><em>LangGraph Workflow Visualization</em>
</p>

| Node | Purpose | Key State Updates |
|------|---------|-------------------|
| `user_interaction` | Chatbot Q&A and booking collection | `bot_response`, `is_booking_flow`, `conversation_phase` |
| `save_reservation` | Persist booking to SQLite | `reservation_id`, `phase → AWAITING_ADMIN` |
| `admin_review` | Parse admin approve/reject decision | `admin_decision`, `admin_notes`, `phase` |
| `notification` | Send email + update DB status | `notification_sent` |
| `mcp_recording` | Write approved reservation to file | `mcp_recorded` |
| `completion` | Generate pipeline summary | `phase → COMPLETED` |

---

## 🛠 Tech Stack

### Backend

| Technology | Purpose |
|-----------|---------|
| Python 3.11 | Runtime |
| FastAPI | REST API framework |
| LangChain | LLM/RAG framework |
| LangGraph | State graph orchestration |
| SQLAlchemy | ORM for SQLite |
| Pinecone | Cloud vector database |
| HuggingFace | Local embeddings (`all-MiniLM-L6-v2`) |
| Presidio | PII detection and anonymization |
| spaCy (`en_core_web_lg`) | NLP model for guardrails |
| Tenacity | Retry with exponential backoff |
| Pydantic Settings | Typed configuration from `.env` |

### Frontend

| Technology | Purpose |
|-----------|---------|
| Next.js 16 | React framework (App Router) |
| TypeScript | Type-safe development |
| Tailwind CSS 4 | Utility-first styling |
| shadcn/ui | Accessible component library |
| Zustand | Lightweight state management |
| Lucide React | Icon library |

### DevOps

| Technology | Purpose |
|-----------|---------|
| Docker & Docker Compose | Containerization |
| GitHub Actions | CI/CD (3 workflows) |
| Terraform | Infrastructure as Code (Render + Vercel) |
| Black + isort + flake8 | Python linting & formatting |
| ESLint + TypeScript | Frontend linting |
| pytest (161 tests) | Backend test suite |

---

## 🎨 Frontend Architecture

The frontend is a **Next.js 16 App Router** application with a clean component hierarchy:

```
frontend/src/
├── app/                    # Next.js routes
│   ├── page.tsx            # Chat interface (home)
│   ├── admin/page.tsx      # Admin dashboard
│   └── layout.tsx          # Root layout with Navbar
├── components/
│   ├── chat/               # ChatWindow, MessageBubble, InputBar
│   ├── admin/              # ReservationTable, AdminLoginGate
│   ├── shared/             # Navbar, Footer
│   └── providers/          # ThemeProvider, Providers wrapper
├── store/
│   └── chatStore.ts        # Zustand store (sessions, messages)
├── services/
│   └── chatService.ts      # API client (fetch wrapper)
├── hooks/
│   └── useMediaQuery.ts    # Responsive design hook
├── lib/
│   └── helpers.ts          # Utility functions
└── types/
    └── index.ts            # Shared TypeScript interfaces
```

**Key patterns:**
- **Zustand** for global chat state (sessions, messages, loading)
- **Server Components** by default, Client Components only where needed
- **Dark/Light theme** via `next-themes` + Tailwind
- **Responsive layout** with mobile-first design

<p align="center">
  <img src="Screenshots/frontend_user_ui.png" alt="Frontend User Chat UI" width="80%">
  <br><em>Chat Interface — User View</em>
</p>

---

## ⚙ Backend Architecture

```
src/
├── api/server.py           # FastAPI app — REST endpoints + chat
├── chatbot/
│   ├── chatbot.py          # Conversation state machine (IDLE → COLLECTING → CONFIRMING)
│   ├── rag_chain.py        # Vector retrieval + LLM generation
│   └── guardrails.py       # Input injection detection + output PII redaction
├── database/
│   ├── sql_store.py        # SQLAlchemy — hours, prices, availability, reservations
│   └── vector_store.py     # Pinecone — static parking knowledge for RAG
├── graph/
│   ├── state.py            # GraphState TypedDict + PipelinePhase enum
│   ├── nodes.py            # 6 processing nodes
│   └── pipeline.py         # StateGraph builder + conditional edges
├── agents/
│   └── admin_agent.py      # LangChain agent with tools for reservation review
├── notifications/
│   └── email_service.py    # SMTP SSL/STARTTLS with retry + console fallback
├── mcp/
│   ├── mcp_server.py       # Tool server (port 8001) with API key auth
│   └── mcp_client.py       # HTTP client with local file fallback
└── utils/
    ├── masking.py           # Email masking (sa****@gmail.com)
    └── logging_config.py    # Structured logging setup
```

**Design principles:**
- **Dual database split** — SQL for transactional data, Pinecone for semantic search
- **Singleton instances** — Graph nodes share chatbot/SQL/email service instances
- **Custom exceptions** — `VectorStoreError`, `EmailServiceError` with retry logic
- **Configuration via Pydantic** — `from config.settings import settings` everywhere

---

## 🗄 Vector Database — Pinecone

Pinecone stores the static parking knowledge base for semantic retrieval:

```
parking_info.txt  →  Chunking (500 chars, 50 overlap)
                         │
                         ▼
              HuggingFace Embeddings (all-MiniLM-L6-v2)
                         │
                         ▼
              Pinecone Index ("parking-info")
                         │
                  User query ──▶ Embed ──▶ Top-K similarity search
                                                │
                                                ▼
                                        Retrieved contexts
```

**What's stored:** Location, facilities, pricing structure, booking rules, cancellation policies, EV charging info, accessibility, security features.

**Why Pinecone over ChromaDB:** Cloud-hosted, zero-ops, scalable, serverless — suitable for production deployment.

<p align="center">
  <img src="Screenshots/pinecone_vector_db.png" alt="Pinecone Vector DB" width="80%">
  <br><em>Pinecone Vector Database Index</em>
</p>

---

## 📚 RAG Pipeline

The Retrieval-Augmented Generation pipeline combines vector search with LLM generation:

```
User Question
      │
      ▼
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│  Embed query │────▶│ Pinecone search   │────▶│ Top-K docs  │
│  (MiniLM)    │     │ (similarity)      │     │ (context)   │
└─────────────┘     └──────────────────┘     └──────┬──────┘
                                                     │
                                              ┌──────▼──────┐
                                              │ Prompt:       │
                                              │ System +      │
                                              │ Context +     │
                                              │ SQL data +    │
                                              │ User query    │
                                              └──────┬──────┘
                                                     │
                                              ┌──────▼──────┐
                                              │ GPT-4o (DIAL)│
                                              └──────┬──────┘
                                                     │
                                              ┌──────▼──────┐
                                              │ Guardrails   │
                                              │ PII filter   │
                                              └──────┬──────┘
                                                     │
                                                     ▼
                                               Response to user
```

**Dual data sources:**
- **Pinecone** — Static knowledge (location, facilities, policies)
- **SQLite** — Dynamic data (real-time hours, prices, availability counts)

The RAG chain merges both sources into the LLM prompt for accurate, up-to-date answers.

---

## 🧑‍💼 Human-in-the-Loop Workflow

The admin review is a **graph-pausing mechanism** where the LangGraph pipeline waits for human input:

1. **User completes booking** → Graph auto-advances to `admin_review`
2. **`admin_review` node** generates a review summary with availability data
3. **Graph pauses** — sets `needs_admin_input = True` and returns `END`
4. **Admin reviews** via the dashboard or CLI → types `approve` or `reject`
5. **Pipeline resumes** → `notification` → `mcp_recording` → `completion`

The admin always makes the final decision. The graph routes it automatically.

---

## 📧 SMTP Notification Workflow

```
Reservation Event
       │
       ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Build HTML   │────▶│ SMTP Connect  │────▶│ Send Email   │
│ template     │     │ (SSL/STARTTLS)│     │ with retry   │
└──────────────┘     └──────────────┘     └──────────────┘
```

**Notification triggers:**
- New reservation submitted → Admin notified
- Reservation approved → User notified with confirmation
- Reservation rejected → User notified with reason

**Resilience:**
- Automatic retry with exponential backoff (Tenacity)
- SSL (port 465) and STARTTLS (port 587) support
- Console fallback when SMTP is not configured
- Email masking in logs (`sa****@gmail.com`)

<p align="center">
  <img src="Screenshots/admin_email_received_.png" alt="Admin Email Received" width="60%">
  <br><em>Email Notification — Admin Receives Booking Request</em>
</p>

---

## 📊 Admin Dashboard

The admin dashboard (`/admin`) provides a web interface for reservation management:

| Feature | Description |
|---------|-------------|
| **Reservation List** | View all reservations with status badges |
| **Status Filters** | Filter by pending, approved, rejected |
| **Quick Actions** | One-click approve/reject with optional notes |
| **Real-time Updates** | Auto-refresh after admin actions |
| **Responsive Design** | Works on desktop and mobile |

<p align="center">
  <img src="Screenshots/frontend_admin_ui.png" alt="Frontend Admin Dashboard" width="80%">
  <br><em>Admin Dashboard — Reservation Management</em>
</p>

---

## 🛡 Security Features

| Layer | Mechanism | Implementation |
|-------|-----------|----------------|
| **Input** | Prompt injection detection | Pattern matching + NLP analysis |
| **Input** | Input sanitization | Length limits, character validation |
| **Output** | PII redaction | Microsoft Presidio with spaCy NER |
| **Output** | Email masking | Custom `mask_email()` utility |
| **API** | CORS configuration | Whitelisted origins only |
| **MCP** | API key authentication | `X-MCP-API-KEY` header validation |
| **Docker** | Non-root container user | `parksmart` user with limited permissions |
| **Config** | Secret management | Pydantic Settings from `.env` (never committed) |

<p align="center">
  <img src="Screenshots/blocking_sesnitive_info.png" alt="Guardrails Blocking Sensitive Info" width="80%">
  <br><em>Guardrails — Prompt Injection / PII Blocked</em>
</p>

---

## 🐳 Docker Setup

### Multi-Stage Dockerfile (Backend)

```dockerfile
# Stage 1: Builder — installs deps in virtualenv
FROM python:3.11-slim AS builder
RUN python -m venv /opt/venv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_lg

# Stage 2: Runtime — copies venv, runs as non-root
FROM python:3.11-slim AS runtime
RUN groupadd -r parksmart && useradd -r -g parksmart parksmart
COPY --from=builder /opt/venv /opt/venv
COPY src/ config/ data/ main.py ./
USER parksmart
CMD ["uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```bash
# Build and start all services
docker compose up --build

# Start in detached mode
docker compose up -d

# View logs
docker compose logs -f backend

# Stop and clean up
docker compose down -v
```

**Services:**

| Service | Port | Health Check |
|---------|------|-------------|
| `backend` (FastAPI) | 8000 | `GET /api/health` |
| `frontend` (Next.js) | 3000 | HTTP probe |

---

## 🔁 CI/CD Pipeline

Three GitHub Actions workflows run on every push to `main`:

### 1. Backend CI (`backend-ci.yml`)

```
Lint & Format Check ──▶ Test Suite ──▶ Validate FastAPI Startup
     │                       │
     ├─ Black               ├─ 161 pytest tests
     ├─ isort               ├─ Coverage report
     ├─ flake8              └─ spaCy model verification
     └─ mypy
```

### 2. Frontend CI (`frontend-ci.yml`)

```
Lint & TypeScript Check ──▶ Production Build
     │                          │
     ├─ ESLint                  └─ next build
     └─ tsc --noEmit
```

### 3. Docker Build & Validate (`docker-build.yml`)

```
Build Backend Image ──┐
                      ├──▶ Validate Compose ──▶ Validate Terraform
Build Frontend Image ──┘        │
                           docker compose up
                           health check verification
```

<p align="center">
  <img src="Screenshots/git_CI-CD_passes.png" alt="CI/CD Pipeline Passes" width="80%">
  <br><em>GitHub Actions — All CI/CD Workflows Passing</em>
</p>

---

## 🌍 Terraform Infrastructure

Infrastructure as Code for deploying to **Render** (backend) and **Vercel** (frontend):

```
terraform/
├── provider.tf     # Render provider configuration
├── main.tf         # Web service resource definition
├── variables.tf    # Configurable parameters (API keys, region, plan)
└── outputs.tf      # Deployment URLs and next steps
```

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

**Resources provisioned:**
- Render Web Service for FastAPI backend (with build command, health check)
- Environment variables injected securely via Terraform variables
- Vercel deployment guide in outputs (manual via CLI)

---

## 📡 API Endpoints

### Chat API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Send a message to the chatbot |

### Reservation API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/reservations` | Submit a new reservation |
| `GET` | `/api/reservations` | List reservations (filter: `?status=pending`) |
| `GET` | `/api/reservations/{id}` | Get reservation details |
| `PUT` | `/api/reservations/{id}/approve` | Admin approves a reservation |
| `PUT` | `/api/reservations/{id}/reject` | Admin rejects a reservation |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/docs` | Swagger UI (interactive API docs) |

### MCP Server (Port 8001)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/mcp/health` | No | Health check |
| `POST` | `/mcp/tools/list` | API Key | Discover available tools |
| `POST` | `/mcp/tools/call` | API Key | Execute a tool |

<p align="center">
  <img src="Screenshots/mcp_configured.png" alt="MCP Server Configured" width="80%">
  <br><em>MCP Tool Server — Configured & Running</em>
</p>

---

## 🚀 Installation

### Prerequisites

- Python 3.10+ (3.11 recommended)
- Node.js 20+ (for frontend)
- EPAM DIAL API key (Azure OpenAI proxy)
- Pinecone API key ([pinecone.io](https://app.pinecone.io))

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/sanyam991/parking-chatbot.git
cd parking-chatbot

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_lg

# Configure environment
copy .env.example .env       # Windows
# cp .env.example .env       # Linux/Mac
# Edit .env with your API keys

# Initialize databases
python main.py --setup
```

### Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local → NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 💻 Local Development

```bash
# Terminal 1: Start backend API
python -m uvicorn src.api.server:app --reload --port 8000

# Terminal 2: Start frontend dev server
cd frontend && npm run dev

# Terminal 3 (optional): Start MCP server
python main.py --mcp-server

# Terminal 4 (optional): Run LangGraph pipeline in CLI mode
python main.py --graph
```

### All CLI Modes

| Command | Description |
|---------|-------------|
| `python main.py` | Chatbot Q&A (terminal) |
| `python main.py --setup` | Initialize databases |
| `python main.py --evaluate` | RAG evaluation metrics |
| `python main.py --server` | REST API (port 8000) |
| `python main.py --admin` | Admin CLI agent |
| `python main.py --mcp-server` | MCP server (port 8001) |
| `python main.py --graph` | LangGraph pipeline |

---

## � PostgreSQL Integration

ParkSmart ships with a **dual-database design**:

| Database | Purpose | When used |
|----------|---------|-----------|
| **SQLite** (default) | Legacy chatbot store — working hours, prices, availability, reservations | Always (chatbot + LangGraph pipeline) |
| **PostgreSQL** | Production transactional store — ParkingType, ParkingSlot, Booking, AdminAction | When `DATABASE_URL` is configured |
| **Pinecone** | Vector store for RAG knowledge retrieval | Always (RAG pipeline) |

### Enabling PostgreSQL

```bash
# 1. Install the driver (already in requirements.txt)
pip install psycopg2-binary alembic

# 2. Create a PostgreSQL database
createdb parksmart

# 3. Uncomment and fill in .env
# DATABASE_URL=postgresql://user:password@localhost:5432/parksmart

# 4. Run migrations
alembic upgrade head

# 5. Seed parking types and slots
python scripts/seed_parking_data.py
```

### New API Endpoints (Production Bookings)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/bookings` | Create a booking |
| `GET` | `/api/bookings` | List bookings (filter by `?status=`) |
| `GET` | `/api/bookings/by-email?email=` | Booking history for a user |
| `GET` | `/api/bookings/reference/{ref}` | Look up by `PS-XXXXX` reference |
| `GET` | `/api/bookings/{id}` | Get booking by ID |
| `POST` | `/api/bookings/{id}/approve` | Admin: approve + assign slot |
| `POST` | `/api/bookings/{id}/reject` | Admin: reject with remarks |
| `POST` | `/api/bookings/{id}/cancel` | Cancel a booking |
| `GET` | `/api/parking/live-status` | Colour-coded availability (`green`/`yellow`/`red`) |
| `POST` | `/api/bookings/check-availability` | Check availability + get alternatives |

### Architecture Layers

```
src/models/          ← SQLAlchemy ORM models (ParkingType, ParkingSlot, Booking, AdminAction)
src/repositories/    ← Data access layer (ParkingRepository, BookingRepository, SlotRepository)
src/services/        ← Business logic (BookingService, PricingService, AvailabilityService, ...)
alembic/             ← Database migrations (alembic upgrade head)
scripts/             ← Seed script (seed_parking_data.py — idempotent, safe to re-run)
```

### Pricing (INR only)

| Duration | Tier used |
|----------|-----------|
| < 24 hours | Hourly rate (`hourly_price`) |
| 24 h – 30 days | Daily rate (`daily_price`) |
| ≥ 30 days | Monthly rate (`monthly_price`) |

All prices are in **Indian Rupees (₹)**. No USD conversion anywhere.

---



Copy `.env.example` to `.env` and configure:

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `DIAL_API_KEY` | Yes | EPAM DIAL API key for GPT-4o | — |
| `PINECONE_API_KEY` | Yes | Pinecone vector database key | — |
| `AZURE_ENDPOINT` | No | DIAL proxy URL | `https://ai-proxy.lab.epam.com` |
| `LLM_MODEL` | No | LLM model name | `gpt-4o` |
| `EMBEDDING_MODEL` | No | Local embedding model | `all-MiniLM-L6-v2` |
| `PINECONE_INDEX_NAME` | No | Pinecone index name | `parking-info` |
| `PINECONE_ENVIRONMENT` | No | Pinecone region | `us-east-1` |
| `SQL_DATABASE_URL` | No | SQLite connection string | `sqlite:///./data/parking_dynamic.db` |
| `DATABASE_URL` | No | PostgreSQL URL — leave blank for SQLite | `""` (SQLite used) |
| `GUARDRAILS_ENABLED` | No | Enable PII/injection protection | `true` |
| `SMTP_HOST` | No | Email server hostname | `smtp.gmail.com` |
| `SMTP_PORT` | No | Email server port | `465` |
| `SMTP_USERNAME` | No | Email account | — |
| `SMTP_PASSWORD` | No | Email app password | — |
| `ADMIN_EMAIL` | No | Admin notification address | — |
| `MCP_SERVER_URL` | No | MCP server URL | `http://localhost:8001` |
| `MCP_API_KEY` | No | MCP server API key | `mcp-parksmart-secret-key-2026` |

> **Important:** Always use `from config.settings import settings` to read config — never raw `os.getenv()`.

---

## 🗃 Database & Slot Inventory

<p align="center">
  <img src="Screenshots/parking_db.png" alt="Parking Database" width="80%">
  <br><em>SQLite Database — Reservations & Dynamic Data</em>
</p>

<p align="center">
  <img src="Screenshots/slot_inventory.png" alt="Slot Inventory" width="80%">
  <br><em>Parking Slot Inventory</em>
</p>

---

## 🧪 Testing

```bash
# Run all 209 tests
python -m pytest tests/ -v

# Run with coverage report
python -m pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing

# Run a specific test file
python -m pytest tests/test_graph.py -v

# Run RAG evaluation
python main.py --evaluate
```

### Test Breakdown

| Module | File | Tests | Scope |
|--------|------|-------|-------|
| Vector Store | `test_vector_store.py` | 4 | Pinecone operations |
| SQL Store | `test_sql_store.py` | 9 | CRUD + dynamic data |
| Chatbot | `test_chatbot.py` | 8 | State machine + RAG |
| Guardrails | `test_guardrails.py` | 14 | PII + injection detection |
| Evaluator | `test_evaluator.py` | 6 | Metrics + latency |
| API Server | `test_api_server.py` | 12 | REST endpoints |
| Admin Agent | `test_admin_agent.py` | 9 | Tools + CLI agent |
| Email Service | `test_email_service.py` | 6 | SMTP + console fallback |
| MCP Server/Client | `test_mcp.py` | 21 | Tools + fallback |
| LangGraph Pipeline | `test_graph.py` | 38 | Nodes + edges + E2E |
| Pricing Service | `test_pricing_service.py` | 11 | INR tiers, no USD |
| Booking Validation | `test_booking_validation.py` | 8 | Rules + alternatives |
| Availability Service | `test_availability_service.py` | 11 | Slots, status, decrement |
| Booking Service | `test_booking_service.py` | 12 | CRUD + approve/reject |
| **Total** | **14 files** | **209** | **All passing** |

**Testing conventions:**
- All external services (LLM, Pinecone, SMTP) are mocked
- In-memory SQLite for database tests
- Async tests use `@pytest.mark.asyncio`
- Mock `settings` object, not `os.environ`

<p align="center">
  <img src="Screenshots/test_evaluator_passes.png" alt="Test Evaluator Passes" width="80%">
  <br><em>RAG Evaluator — All Tests Passing</em>
</p>

---

## 🚢 Deployment Guide

### Option 1: Docker Compose (Recommended)

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with production API keys

# 2. Build and deploy
docker compose up --build -d

# 3. Verify
curl http://localhost:8000/api/health
curl http://localhost:3000
```

### Option 2: Terraform (Cloud)

```bash
cd terraform

# Set secrets
export TF_VAR_render_api_key="your-render-key"
export TF_VAR_dial_api_key="your-dial-key"
export TF_VAR_pinecone_api_key="your-pinecone-key"

terraform init
terraform plan
terraform apply
```

### Option 3: Manual Deployment

1. **Backend** → Deploy to Render, Railway, or any Python host
2. **Frontend** → Deploy to Vercel: `cd frontend && vercel --prod`
3. **Set environment variables** on both platforms

---

## 📸 Screenshots

### Project Structure
![Clean Project Structure](Screenshots/clean_project_structure.png)

### Chat Interface — User Interaction
![User Interaction](Screenshots/user_interaction.png)

### Frontend — User Chat UI
![Frontend User UI](Screenshots/frontend_user_ui.png)

### Booking Flow
![Booking Flow Started](Screenshots/booking_flow_started.png)

### Admin Dashboard
![Admin Dashboard](Screenshots/admin_dashboard.png)

### Frontend — Admin UI
![Frontend Admin UI](Screenshots/frontend_admin_ui.png)

### Booking Approved
![Booking Approved](Screenshots/booking_approved.png)

### Approved Booking Written to File (MCP)
![Approved Booking Written](Screenshots/appoved_booking_wriiten.png)

### Admin Email Received
![Admin Email Received](Screenshots/admin_email_received_.png)

### Guardrails — Blocking Sensitive Info
![Blocking Sensitive Info](Screenshots/blocking_sesnitive_info.png)

### LangGraph Workflow
![LangGraph Workflow](Screenshots/langgraph_workflow.png)

### MCP Server Configured
![MCP Configured](Screenshots/mcp_configured.png)

### Parking Database (SQLite)
![Parking DB](Screenshots/parking_db.png)

### Slot Inventory
![Slot Inventory](Screenshots/slot_inventory.png)

### Pinecone Vector Database
![Pinecone Vector DB](Screenshots/pinecone_vector_db.png)

### CI/CD Pipeline Passing
![Git CI/CD Passes](Screenshots/git_CI-CD_passes.png)

### RAG Evaluator Tests Passing
![Test Evaluator Passes](Screenshots/test_evaluator_passes.png)

---

## 🎮 Demo Access

### Admin Portal

Access the admin dashboard to review and manage reservations:

| Field | Value |
|-------|-------|
| **URL** | `http://localhost:3000/admin` |
| **Username** | `admin` |
| **Password** | `1234` |

### How to Test the Full Workflow

1. **Start the backend:** `python -m uvicorn src.api.server:app --reload --port 8000`
2. **Start the frontend:** `cd frontend && npm run dev`
3. **Open the chat:** Navigate to `http://localhost:3000`
4. **Ask a question:** *"What are your parking rates?"* — tests RAG pipeline
5. **Make a booking:** *"I want to reserve a spot"* — follow the prompts
6. **Review as admin:** Navigate to `http://localhost:3000/admin` → login → approve/reject
7. **Check email:** If SMTP is configured, notification emails are sent automatically

### Sample Chat Interactions

```
You: Where is ParkSmart located?
Bot: ParkSmart is at 123 Main Street, Downtown Business District...

You: I want to book a parking spot
Bot: I'll help you with that! Please provide your full name:

You: John Doe
Bot: Please provide your vehicle registration number:
...
```

---

## 🔮 Future Enhancements

- [ ] **Payment Integration** — Stripe/Razorpay for online parking payments
- [ ] **Real-time Availability Map** — Interactive parking lot visualization
- [ ] **Mobile App** — React Native companion app
- [ ] **Multi-language Support** — i18n for international users
- [ ] **Analytics Dashboard** — Occupancy trends, revenue reports
- [ ] **WebSocket Chat** — Real-time streaming responses
- [ ] **OAuth 2.0** — Google/GitHub login for users and admins
- [ ] **Rate Limiting** — API throttling for production hardening
- [ ] **Kubernetes Deployment** — Helm charts for cloud-native scaling

---

## 👥 Contributors

| Name | Role | Contact |
|------|------|---------|
| **Sanyam Sachan** | Full-Stack Developer | [GitHub](https://github.com/sanyam991) |

---

## 📝 License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with ❤️ using LangChain, LangGraph, FastAPI, Next.js, and Pinecone**

[⬆ Back to Top](#-parksmart--ai-parking-reservation-platform)

</div>
