# module "records" {
#   source  = "terraform-aws-modules/route53/aws//modules/records"
#   version = "~> 3.0"

#   zone_id = var.zone_id

#   records = [
#     {
#       name    = ""
#       type    = "MX"
#       ttl     = 300
#       records = ["10 inbound-smtp.ap-northeast-1.amazonaws.com"]
#     }
#   ]
# }
