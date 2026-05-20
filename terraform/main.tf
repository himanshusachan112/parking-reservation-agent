# ============================================
# Main Infrastructure — Render Backend
# ============================================
# Provisions a Render web service for the FastAPI backend.
# Vercel frontend deployment is handled via Vercel CLI/dashboard
# (no official Terraform provider yet — see outputs for steps).
# ============================================

provider "render" {
  api_key = var.render_api_key
}

# ---- Render Backend Web Service ----
resource "render_web_service" "backend" {
  name        = var.backend_name
  region      = var.backend_region
  plan        = var.backend_plan
  runtime     = "python"

  # Build configuration
  build_command = "pip install -r requirements.txt && python -m spacy download en_core_web_lg && python main.py --setup"
  start_command = "uvicorn src.api.server:app --host 0.0.0.0 --port $PORT"

  # Environment variables
  env_vars = {
    PYTHON_VERSION       = var.python_version
    DIAL_API_KEY         = var.dial_api_key
    PINECONE_API_KEY     = var.pinecone_api_key
    PINECONE_INDEX_NAME  = "parking-info"
    PINECONE_ENVIRONMENT = "us-east-1"
    PINECONE_CLOUD       = "aws"
    SMTP_HOST            = var.smtp_host
    SMTP_PORT            = tostring(var.smtp_port)
    SMTP_USERNAME        = var.smtp_username
    SMTP_PASSWORD        = var.smtp_password
    ADMIN_EMAIL          = var.admin_email
    GUARDRAILS_ENABLED   = "true"
  }

  # Health check
  health_check_path = "/api/health"
}
