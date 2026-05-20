# ============================================
# ParkSmart — Terraform Infrastructure as Code
# ============================================
# Beginner-friendly Terraform setup for deploying ParkSmart
# to Render (backend) and Vercel (frontend).
#
# Usage:
#   cd terraform
#   terraform init
#   terraform plan
#   terraform apply
#
# Prerequisites:
#   - Terraform >= 1.5 installed
#   - Render API key (https://render.com/docs/api)
#   - Vercel API token (https://vercel.com/account/tokens)
# ============================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    # Render provider for backend deployment
    render = {
      source  = "render-oss/render"
      version = "~> 1.0"
    }
  }
}
