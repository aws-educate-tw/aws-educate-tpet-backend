# module "zones" {
#   source  = "terraform-aws-modules/route53/aws//modules/zones"
#   version = "~> 3.0"

#   zones = {
#     "aws-educate.tw" = {
#       comment = "aws-educate.tw"
#     }
#   }

#   tags = {
#     ManagedBy = "Terraform"
#   }
# }

module "records" {
  source  = "terraform-aws-modules/route53/aws//modules/records"
  version = "~> 3.0"

#   zone_name = keys(module.zones.route53_zone_zone_id)[0]
  zone_id = var.zone_id

  records = [
    {
      name    = ""
      type    = "MX"
      ttl     = 300
      records = ["10 inbound-smtp.ap-northeast-1.amazonaws.com"]
    }
  ]
  depends_on = [module.zones]
}
