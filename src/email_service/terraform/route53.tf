data "aws_route53_zone" "awseducate_systems" {
  name         = var.domain_name
  private_zone = false
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
