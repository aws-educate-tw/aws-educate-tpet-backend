locals {
  region             = var.aws_region
  custom_domain_name = "${var.environment}-${var.service_hyphen}-internal-api-tpet.aws-educate.tw"
  sub_domain_name    = "${var.environment}-${var.service_hyphen}-internal-api-tpet"

  tags = {
    Service = var.service_underscore
  }
}

# Find a certificate that is issued
data "aws_acm_certificate" "issued" {
  domain   = "*.${var.domain_name}"
  statuses = ["ISSUED"]
}

data "aws_route53_zone" "awseducate_systems" {
  name         = var.domain_name
  private_zone = false
}

# Get Lambda authorizer lambda
data "aws_ssm_parameter" "lambda_authorizer_lambda_invoke_arn" {
  name = "${var.environment}-lambda_authorizer_lambda_invoke_arn"
}

################################################################################
# API Gateway Module
################################################################################

module "api_gateway" {
  source  = "terraform-aws-modules/apigateway-v2/aws"
  version = "5.0.0"

  description = "Email service api gateway to lambda container image"
  name        = "${var.environment}-${var.service_underscore}"
  stage_name  = var.environment


  cors_configuration = {
    allow_headers     = ["content-type", "x-amz-date", "authorization", "x-api-key", "x-amz-security-token", "x-amz-user-agent"]
    allow_methods     = ["*"]
    allow_origins     = ["http://localhost:3000", "http://localhost:5500", "https://*"]
    allow_credentials = true
  }

  fail_on_warnings = false

  # Authorizer(s)
  authorizers = {
    lambda_authorizer = {
      name                              = "lambda_authorizer"
      authorizer_type                   = "REQUEST"
      authorizer_uri                    = data.aws_ssm_parameter.lambda_authorizer_lambda_invoke_arn.value
      authorizer_payload_format_version = "2.0"
      enable_simple_responses           = true
    }
  }


  # Custom Domain Name
  domain_name                 = local.custom_domain_name
  domain_name_certificate_arn = data.aws_acm_certificate.issued.arn
  api_mapping_key             = var.environment
  create_domain_records       = false
  create_certificate          = false
  create_domain_name          = true


  # Routes & Integration(s)
  routes = {
    "POST /send-email" = {
      detailed_metrics_enabled = true
      throttling_rate_limit    = 80
      throttling_burst_limit   = 40

      authorization_type = "CUSTOM"
      authorizer_key     = "lambda_authorizer"

      integration = {
        uri                    = module.validate_input_lambda.lambda_function_arn
        type                   = "AWS_PROXY"
        payload_format_version = "1.0"
        timeout_milliseconds   = 29000
      }
    }
  }

  # Stage
  stage_access_log_settings = {
    create_log_group            = true
    log_group_retention_in_days = 7
    format = jsonencode({
      context = {
        domainName              = "$context.domainName"
        integrationErrorMessage = "$context.integrationErrorMessage"
        protocol                = "$context.protocol"
        requestId               = "$context.requestId"
        requestTime             = "$context.requestTime"
        responseLength          = "$context.responseLength"
        routeKey                = "$context.routeKey"
        stage                   = "$context.stage"
        status                  = "$context.status"
        error = {
          message      = "$context.error.message"
          responseType = "$context.error.responseType"
        }
        identity = {
          sourceIP = "$context.identity.sourceIp"
        }
        integration = {
          error             = "$context.integration.error"
          integrationStatus = "$context.integration.integrationStatus"
        }
      }
    })
  }

  stage_default_route_settings = {
    detailed_metrics_enabled = true
    throttling_burst_limit   = 100
    throttling_rate_limit    = 100
  }

  tags = local.tags
}

resource "aws_route53_record" "api_gateway_custom_domain_record" {
  zone_id = data.aws_route53_zone.awseducate_systems.zone_id
  name    = local.custom_domain_name
  type    = "A"

  alias {
    name                   = module.api_gateway.domain_name_target_domain_name
    zone_id                = module.api_gateway.domain_name_hosted_zone_id
    evaluate_target_health = false
  }
}
