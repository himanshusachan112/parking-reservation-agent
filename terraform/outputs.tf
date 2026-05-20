# ============================================
# Outputs — Deployment URLs and next steps
# ============================================

output "backend_url" {
  description = "Render backend service URL"
  value       = render_web_service.backend.url
}

output "backend_health_url" {
  description = "Backend health check endpoint"
  value       = "${render_web_service.backend.url}/api/health"
}

output "vercel_deployment_steps" {
  description = "Steps to deploy frontend on Vercel"
  value       = <<-EOT
    Vercel Frontend Deployment:
    1. Install Vercel CLI: npm i -g vercel
    2. cd frontend
    3. vercel --prod
    4. Set environment variable:
       NEXT_PUBLIC_API_URL = ${render_web_service.backend.url}
    5. Redeploy after setting env var: vercel --prod
  EOT
}
