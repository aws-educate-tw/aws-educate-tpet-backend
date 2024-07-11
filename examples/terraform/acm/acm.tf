provider "aws" {
  region = "us-west-2"
  default_tags {
    tags = {
      "Terraform" = "true",
      "Project"   = "AWS Educate TPET"
    }
  }
}

data "aws_route53_zone" "awseducate_systems" {
  name         = "awseducate.systems"
  private_zone = false
}

resource "aws_route53_record" "file_service_record" {
  for_each = {
    for dvo in aws_acm_certificate.cert.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.awseducate_systems.zone_id
}


resource "aws_acm_certificate" "cert" {
  domain_name       = "file-service.awseducate.systems"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate_validation" "cert_validation" {
  certificate_arn         = aws_acm_certificate.cert.arn
  validation_record_fqdns = [for record in aws_route53_record.file_service_record : record.fqdn]
}
