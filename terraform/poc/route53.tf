module "zones" {
  source  = "terraform-aws-modules/route53/aws//modules/zones"
  version = "3.1.0"

  zones = {
    "${var.domain_name}" = {
      comment = "Managed by Terraform"
    }
  }

  tags = {
    ManagedBy = "Terraform"
  }
}

module "records" {
  source  = "terraform-aws-modules/route53/aws//modules/records"
  version = "3.1.0"

  zone_name = var.domain_name

  records = [
    {
      name = ""
      type = "A"
      alias = {
        name    = module.cloudfront.cloudfront_distribution_domain_name
        zone_id = module.cloudfront.cloudfront_distribution_hosted_zone_id
      }
    }
  ]

  depends_on = [module.zones]
}
