locals {
  # Determine base URL pattern based on environment
  api_base_url = var.environment == "local-dev" ? (
    "https://${var.environment}-{service}-internal-api-tpet.${var.domain_name}"
  ) : (
    "https://api.tpet.${var.domain_name}"
  )

  service_endpoints = {
    email = var.environment == "local-dev" ? (
      replace(local.api_base_url, "{service}", "email-service")
    ) : (
      local.api_base_url
    )
    webhook = var.environment == "local-dev" ? (
      replace(local.api_base_url, "{service}", "webhook-service")
    ) : (
      local.api_base_url
    )
  }

  api_endpoints = {
    send_email      = "${local.service_endpoints.email}/${var.environment}/send-email"
    trigger_webhook = "${local.service_endpoints.webhook}/${var.environment}/trigger-webhook"
  }
}
