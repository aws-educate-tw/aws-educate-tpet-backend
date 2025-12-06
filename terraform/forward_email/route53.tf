data "aws_route53_zone" "aws_educate_tpet_domain" {
  name         = var.domain_name
  private_zone = false
}

# SES Domain Verification TXT Record
# resource "aws_route53_record" "ses_verification_record" {
#   zone_id = data.aws_route53_zone.aws_educate_tpet_domain.zone_id
#   name    = "_amazonses.${var.domain_name}"
#   type    = "TXT"
#   ttl     = 600
#   records = [aws_ses_domain_identity.ses_aws_educate_tpet_domain.verification_token]
# }

# MX Record for SES Email Receiving
resource "aws_route53_record" "ses_mx_record" {
  zone_id = data.aws_route53_zone.aws_educate_tpet_domain.zone_id
  name    = var.domain_name
  type    = "MX"
  ttl     = 600
  records = ["10 inbound-smtp.${var.aws_region}.amazonaws.com"]
}
