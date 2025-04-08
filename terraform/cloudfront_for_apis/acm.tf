# Find a certificate that is issued
# 手動去 console 申請一個 ACM 證書
# data "aws_acm_certificate" "issued_api_tpet_cert" {
#   domain   = "api.tpet.${var.domain_name}"
#   statuses = ["ISSUED"]
# }

module "api_tpet_cert" {
  source  = "terraform-aws-modules/acm/aws"
  version = "~> 5.0.0"

  domain_name = "api.tpet.${var.domain_name}"
  zone_id     = data.aws_route53_zone.awseducate_systems.zone_id

  validation_method = "DNS"

  subject_alternative_names = [
    "api.tpet.${var.domain_name}"
  ]

  wait_for_validation = true
}
