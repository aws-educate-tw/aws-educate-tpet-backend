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
    # Email Service - prod
    domain_name  = "prod-email-service-internal-api-tpet.awseducate.systems"
    path_pattern = "/prod/*email*"
  },
  {
    # Email Service - dev
    domain_name  = "dev-email-service-internal-api-tpet.awseducate.systems"
    path_pattern = "/dev/*email*"
  }
]
