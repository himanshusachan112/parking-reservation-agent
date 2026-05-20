# ============================================
# Variables — Configurable deployment parameters
# ============================================
# Set these in terraform.tfvars or via environment:
#   export TF_VAR_render_api_key="your-key"
# ============================================

# ---- Provider Credentials ----

variable "render_api_key" {
  description = "Render API key for deploying the backend service"
  type        = string
  sensitive   = true
}

variable "vercel_api_token" {
  description = "Vercel API token for frontend deployment"
  type        = string
  sensitive   = true
  default     = ""
}

# ---- Backend Configuration ----

variable "backend_name" {
  description = "Name for the Render backend service"
  type        = string
  default     = "parksmart-api"
}

variable "backend_region" {
  description = "Render deployment region"
  type        = string
  default     = "oregon"
}

variable "backend_plan" {
  description = "Render instance plan (free, starter, standard, pro)"
  type        = string
  default     = "free"
}

variable "python_version" {
  description = "Python runtime version"
  type        = string
  default     = "3.11.0"
}

# ---- Frontend Configuration ----

variable "frontend_name" {
  description = "Name for the Vercel frontend project"
  type        = string
  default     = "parksmart-frontend"
}

# ---- Application Secrets ----

variable "dial_api_key" {
  description = "EPAM DIAL API key for LLM access"
  type        = string
  sensitive   = true
}

variable "pinecone_api_key" {
  description = "Pinecone API key for vector database"
  type        = string
  sensitive   = true
}

variable "smtp_host" {
  description = "SMTP server hostname"
  type        = string
  default     = "smtp.gmail.com"
}

variable "smtp_port" {
  description = "SMTP server port (465 for SSL, 587 for STARTTLS)"
  type        = number
  default     = 465
}

variable "smtp_username" {
  description = "SMTP authentication username"
  type        = string
  sensitive   = true
  default     = ""
}

variable "smtp_password" {
  description = "SMTP authentication password (app-specific password)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "admin_email" {
  description = "Admin email address for reservation notifications"
  type        = string
  default     = "admin@parksmart.com"
}
