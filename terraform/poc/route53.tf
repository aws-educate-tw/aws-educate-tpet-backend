module "records" {
  source  = "terraform-aws-modules/route53/aws//modules/records"
  version = "3.1.0"

  zone_id = var.zone_id

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
