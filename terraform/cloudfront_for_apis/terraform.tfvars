aws_region         = "us-east-1"
environment        = "global"
service_underscore = "cloudfront_for_apis"
service_hyphen     = "cloudfront-for-apis"
domain_name        = "awseducate.systems"
api_gateway_origins = [
  {
    # Campaign Service - prod
    domain_name  = "prod-campaign-service-internal-api-tpet.awseducate.systems"
    path_pattern = "/prod/*campaign*"
  },
  {
    # Campaign Service - dev
    domain_name  = "dev-campaign-service-internal-api-tpet.awseducate.systems"
    path_pattern = "/dev/*campaign*"
  },
  {
    # File Service - prod
    domain_name  = "prod-file-service-internal-api-tpet.awseducate.systems"
    path_pattern = "/prod/*file*"
  },
  {
    # File Service - dev
    domain_name  = "dev-file-service-internal-api-tpet.awseducate.systems"
    path_pattern = "/dev/*file*"
  },
  {
    # Auth Service - prod
    domain_name  = "prod-auth-service-internal-api-tpet.awseducate.systems"
    path_pattern = "/prod/auth*"
  },
  {
    # Auth Service - dev
    domain_name  = "dev-auth-service-internal-api-tpet.awseducate.systems"
    path_pattern = "/dev/auth*"
  },
  {
    # Webhook Service - prod
    domain_name  = "prod-webhook-service-internal-api-tpet.awseducate.systems"
    path_pattern = "/prod/*webhook*"
  },
  {
    # Webhook Service - dev
    domain_name  = "dev-webhook-service-internal-api-tpet.awseducate.systems"
    path_pattern = "/dev/*webhook*"
  },
  {
    # Email Service - prod
    domain_name  = "prod-email-service-internal-api-tpet.awseducate.systems"
    path_pattern = "/prod/*"
  },
  {
    # Email Service - dev
    domain_name  = "dev-email-service-internal-api-tpet.awseducate.systems"
    path_pattern = "/dev/*"
  }
]
