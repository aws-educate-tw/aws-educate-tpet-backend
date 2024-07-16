
data "aws_route53_zone" "awseducate_systems" {
  name         = var.domain_name
  private_zone = false
}

module "records" {
  source  = "terraform-aws-modules/route53/aws//modules/records"
  version = "3.1.0"

  zone_id = data.aws_route53_zone.awseducate_systems.zone_id

  records = [
    {
      name = "api.tpet"
      type = "A"
      alias = {
        name    = module.cloudfront.cloudfront_distribution_domain_name
        zone_id = module.cloudfront.cloudfront_distribution_hosted_zone_id
      }
    }
  ]
}
