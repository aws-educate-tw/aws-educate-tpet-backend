locals {
  region             = var.aws_region
  custom_domain_name = "${var.environment}.${var.service_hyphen}.internal.api.tpet.awseducate.systems"
  sub_domain_name    = "${var.environment}-${var.service_hyphen}-internal-api-tpet"

  tags = {
    Service = var.service_underscore
  }
}

################################################################################
# API Gateway Module
################################################################################

module "api_gateway" {
  source  = "terraform-aws-modules/apigateway-v2/aws"
  version = "5.0.0"

  description = "File service api gateway to lambda container image"
  name        = "${var.environment}-${var.service_underscore}"
  stage_name  = var.environment


  cors_configuration = {
    allow_headers = ["content-type", "x-amz-date", "authorization", "x-api-key", "x-amz-security-token", "x-amz-user-agent"]
    allow_methods = ["*"]
    allow_origins = ["*"]
  }

  fail_on_warnings = false


  # Custom Domain Name
  domain_name           = "*.${var.domain_name}"
  subdomains            = [local.sub_domain_name]
  create_domain_records = true
  create_certificate    = true
  create_domain_name    = false


  # Routes & Integration(s)
  routes = {
    "ANY /" = {
      detailed_metrics_enabled = false

      integration = {
        uri                    = module.lambda_container_image.lambda_function_arn
        payload_format_version = "1.0"
        timeout_milliseconds   = 29000
      }
    }

    "POST /upload-multiple-file" = {
      detailed_metrics_enabled = true
      throttling_rate_limit    = 80
      throttling_burst_limit   = 40
      integration = {
        uri                    = module.lambda_container_image.lambda_function_arn # Remember to change
        type                   = "AWS_PROXY"
        payload_format_version = "1.0"
        timeout_milliseconds   = 29000
      }
    }

    "GET /files/{file_id}" = {
      detailed_metrics_enabled = true
      throttling_rate_limit    = 80
      throttling_burst_limit   = 40
      integration = {
        uri                    = module.get_file_lambda.lambda_function_arn # Remember to change
        type                   = "AWS_PROXY"
        payload_format_version = "1.0"
        timeout_milliseconds   = 29000
      }
    }



    "$default" = {
      integration = {
        uri = module.lambda_container_image.lambda_function_arn
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
