locals {
  region             = var.aws_region
  custom_domain_name = "${var.environment}-${var.service_hyphen}-internal-api-tpet.${var.domain_name}"
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
  version = "6.1.0"

  description = "RSVP service api gateway in ${var.environment} environment"
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
  api_mapping_key             = "${var.service_hyphen}/${var.environment}"
  create_domain_records       = false
  create_certificate          = false
  create_domain_name          = true

  # Routes & Integration(s)
  routes = {
    "PUT /rsvp/{run_id_participant_id}" = {
      detailed_metrics_enabled = true
      throttling_rate_limit    = 80
      throttling_burst_limit   = 40

      # TODO: Re-enable authorizer after auth flow is ready
      # authorization_type = "CUSTOM"
      # authorizer_key     = "lambda_authorizer"

      integration = {
        uri                    = module.update_rsvp_lambda.lambda_function_arn
        type                   = "AWS_PROXY"
        payload_format_version = "1.0"
        timeout_milliseconds   = 29000
      }
    }

    "GET /rsvp/{run_id_participant_id}/status" = {
      detailed_metrics_enabled = true
      throttling_rate_limit    = 80
      throttling_burst_limit   = 40

      # TODO: Re-enable authorizer after auth flow is ready
      # authorization_type = "CUSTOM"
      # authorizer_key     = "lambda_authorizer"

      integration = {
        uri                    = module.get_rsvp_status_lambda.lambda_function_arn
        type                   = "AWS_PROXY"
        payload_format_version = "1.0"
        timeout_milliseconds   = 29000
      }
    }

    "GET /internal/campaign/{campaign_id}/check" = {
      detailed_metrics_enabled = true
      throttling_rate_limit    = 80
      throttling_burst_limit   = 40

      # TODO: Re-enable authorizer after auth flow is ready
      # authorization_type = "CUSTOM"
      # authorizer_key     = "lambda_authorizer"

      integration = {
        uri                    = module.verify_campaign_lambda.lambda_function_arn
        type                   = "AWS_PROXY"
        payload_format_version = "1.0"
        timeout_milliseconds   = 29000
      }
    }

    "PUT /internal/campaign-runs/{campaign_id_run_id}" = {
      detailed_metrics_enabled = true
      throttling_rate_limit    = 80
      throttling_burst_limit   = 40

      # TODO: Re-enable authorizer after auth flow is ready
      # authorization_type = "CUSTOM"
      # authorizer_key     = "lambda_authorizer"

      integration = {
        uri                    = module.upsert_run_configuration_lambda.lambda_function_arn
        type                   = "AWS_PROXY"
        payload_format_version = "1.0"
        timeout_milliseconds   = 29000
      }
    }

    "POST /internal/runs/{run_id}/participants" = {
      detailed_metrics_enabled = true
      throttling_rate_limit    = 80
      throttling_burst_limit   = 40

      # TODO: Re-enable authorizer after auth flow is ready
      # authorization_type = "CUSTOM"
      # authorizer_key     = "lambda_authorizer"

      integration = {
        uri                    = module.import_participant_lambda.lambda_function_arn
        type                   = "AWS_PROXY"
        payload_format_version = "1.0"
        timeout_milliseconds   = 29000
      }
    }

    "GET /campaigns" = {
      detailed_metrics_enabled = true
      throttling_rate_limit    = 80
      throttling_burst_limit   = 40

      authorization_type = "CUSTOM"
      authorizer_key     = "lambda_authorizer"

      integration = {
        uri                    = module.list_campaigns_lambda.lambda_function_arn
        type                   = "AWS_PROXY"
        payload_format_version = "1.0"
        timeout_milliseconds   = 29000
      }
    }

    "GET /campaigns/{campaign_id}" = {
      detailed_metrics_enabled = true
      throttling_rate_limit    = 80
      throttling_burst_limit   = 40

      authorization_type = "CUSTOM"
      authorizer_key     = "lambda_authorizer"

      integration = {
        uri                    = module.get_campaign_lambda.lambda_function_arn
        type                   = "AWS_PROXY"
        payload_format_version = "1.0"
        timeout_milliseconds   = 29000
      }
    }

    "POST /campaigns" = {
      detailed_metrics_enabled = true
      throttling_rate_limit    = 80
      throttling_burst_limit   = 40

      # TODO: Re-enable authorizer after auth flow is ready
      # authorization_type = "CUSTOM"
      # authorizer_key     = "lambda_authorizer"

      integration = {
        uri                    = module.create_campaign_lambda.lambda_function_arn
        type                   = "AWS_PROXY"
        payload_format_version = "1.0"
        timeout_milliseconds   = 29000
      }
    }
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
