module "api_gateway" {
  source  = "terraform-aws-modules/apigateway-v2/aws"
  version = "5.0.0"

  name          = "onboarding-${var.environment}"
  description   = "TPET onboarding API (${var.environment})"
  protocol_type = "HTTP"

  # Stage
  create_stage = true
  stage_name   = var.environment

  create_domain_name    = false
  create_domain_records = false

  # Routes & Integrations
  routes = {
    "GET /onboarding/{name}" = {
      integration = {
        uri                    = module.onboarding_lambda.lambda_function_arn
        type                   = "AWS_PROXY"
        payload_format_version = "2.0"
      }
    }
  }
}
