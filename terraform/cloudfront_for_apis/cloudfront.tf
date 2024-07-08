module "cloudfront" {
  source  = "terraform-aws-modules/cloudfront/aws"
  version = "3.4.0"

  aliases = [var.domain_name]

  comment             = "CloudFront distribution for multiple API Gateways"
  enabled             = true
  is_ipv6_enabled     = true
  price_class         = "PriceClass_200"
  retain_on_delete    = false
  wait_for_deployment = false


  origin = {
    for o in var.api_gateway_origins : o.domain_name => {
      domain_name = o.domain_name
      custom_origin_config = {
        http_port              = 80
        https_port             = 443
        origin_protocol_policy = "https-only"
        origin_ssl_protocols   = ["TLSv1.2"]
      }
    }
  }

  default_cache_behavior = {
    target_origin_id       = var.api_gateway_origins[0].domain_name
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    query_string           = true
    headers                = ["Origin", "Access-Control-Request-Headers", "Access-Control-Request-Method"]
  }

  ordered_cache_behavior = [
    for o in var.api_gateway_origins :
    {
      path_pattern           = o.path_pattern
      target_origin_id       = o.domain_name
      viewer_protocol_policy = "redirect-to-https"
      allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
      cached_methods         = ["GET", "HEAD"]
      compress               = true
      query_string           = true
      headers                = ["Origin", "Access-Control-Request-Headers", "Access-Control-Request-Method"]
    }
  ]

  viewer_certificate = {
    acm_certificate_arn = module.api_tpet_cert.acm_certificate_arn
    ssl_support_method  = "sni-only"
  }
}
