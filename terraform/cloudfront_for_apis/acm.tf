data "aws_route53_zone" "awseducate_systems" {
  name         = var.domain_name
  private_zone = false
}


module "api_tpet_cert" {
  source  = "terraform-aws-modules/acm/aws"
  version = "~> 5.0.0"

  domain_name = "api.tpet.${var.domain_name}"
  zone_id     = data.aws_route53_zone.awseducate_systems.zone_id

  validation_method = "DNS"

  subject_alternative_names = [
    "*.api.tpet.${var.domain_name}",
    "api.tpet.${var.domain_name}",
  ]

  wait_for_validation = true
}
