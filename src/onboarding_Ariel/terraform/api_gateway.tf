################################################################################
# API Gateway Module (v2 HTTP API)
################################################################################

module "api_gateway" {
  source  = "terraform-aws-modules/apigateway-v2/aws"
  version = "5.0.0"

  name        = "onboarding-ariel-api"
  description = "Ariel Onboarding API to lambda container image"
  stage_name  = var.environment

  cors_configuration = {
    allow_headers     = ["content-type", "x-amz-date", "authorization", "x-api-key", "x-amz-security-token", "x-amz-user-agent"]
    allow_methods     = ["*"]
    allow_origins     = ["*"]
    allow_credentials = true
  }

  fail_on_warnings = false

  # Routes & Integration(s)
  routes = {
    "GET /onboarding/{newbie_name}" = {
      detailed_metrics_enabled = true
      throttling_rate_limit    = 100
      throttling_burst_limit   = 100
      integration = {
        uri                    = module.onboarding_lambda.lambda_function_arn
        type                   = "AWS_PROXY"
        payload_format_version = "1.0"
        timeout_milliseconds   = 29000
      }
    }
  }

  # Stage Access Log Settings
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

  tags = {
    Environment = var.environment
  }
}