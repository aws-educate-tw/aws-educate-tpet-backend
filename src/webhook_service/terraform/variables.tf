variable "aws_region" {
  description = "aws region"
}

variable "environment" {
  description = "Current environtment: prod(ap-northeast-1)/dev(us-east-1)/local-dev(us-west-2), default dev(us-east-1)"
  validation {
    condition     = contains(["prod", "dev", "local-dev"], var.environment)
    error_message = "Environment must be one of: prod, dev, local-dev"
  }
}

variable "service_underscore" {
  description = "Current service name"
}

variable "service_hyphen" {
  description = "This variable contains the current service name, but with hyphens instead of underscores. For example: demo-service."
}

variable "domain_name" {
  description = "Domain name, for example: example.com"
  default     = "aws-educate.tw"
}

variable "dynamodb_table" {
  description = "Current service's DynamoDB table name"
}

variable "enable_pitr" {
  description = "Enable Point-In-Time Recovery for DynamoDB tables"
  type        = bool
}

variable "enable_deletion_protection_for_dynamodb_table" {
  description = "Enable deletion protection for DynamoDB tables"
  type        = bool
}

variable "docker_host" {
  description = "Docker host"
  type        = string
}

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
