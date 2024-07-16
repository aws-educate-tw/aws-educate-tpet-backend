module "cloudfront" {
  source  = "terraform-aws-modules/cloudfront/aws"
  version = "3.4.0"

  aliases = ["api.tpet.${var.domain_name}"]

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
    target_origin_id         = var.api_gateway_origins[0].domain_name
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods           = ["GET", "HEAD"]
    compress                 = true
    query_string             = true
    cache_policy_id          = aws_cloudfront_cache_policy.custom_cache_policy.id
    origin_request_policy_id = aws_cloudfront_origin_request_policy.custom_origin_request_policy.id
    use_forwarded_values     = false
  }

  ordered_cache_behavior = [
    for o in var.api_gateway_origins :
    {
      path_pattern             = o.path_pattern
      target_origin_id         = o.domain_name
      viewer_protocol_policy   = "redirect-to-https"
      allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
      cached_methods           = ["GET", "HEAD"]
      compress                 = true
      query_string             = true
      cache_policy_id          = aws_cloudfront_cache_policy.custom_cache_policy.id
      origin_request_policy_id = aws_cloudfront_origin_request_policy.custom_origin_request_policy.id
      use_forwarded_values     = false
    }
  ]

  viewer_certificate = {
    acm_certificate_arn = data.aws_acm_certificate.issued_api_tpet_cert.arn
    ssl_support_method  = "sni-only"
  }
}

resource "aws_cloudfront_cache_policy" "custom_cache_policy" {
  name        = "custom-cache-policy"
  comment     = "Custom cache policy for disabling Set-Cookie header caching"
  default_ttl = 86400
  max_ttl     = 31536000
  min_ttl     = 0

  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config {
      cookie_behavior = "none"
    }
    headers_config {
      header_behavior = "whitelist"
      headers {
        items = ["Set-Cookie"]
      }
    }
    query_strings_config {
      query_string_behavior = "all"
    }
    enable_accept_encoding_gzip = true
  }
}

resource "aws_cloudfront_origin_request_policy" "custom_origin_request_policy" {
  name    = "custom-origin-request-policy"
  comment = "Custom origin request policy for forwarding Set-Cookie header"

  cookies_config {
    cookie_behavior = "all"
  }
  headers_config {
    header_behavior = "whitelist"
    headers {
      items = ["Origin", "Access-Control-Request-Headers", "Access-Control-Request-Method", "Set-Cookie"]
    }
  }
  query_strings_config {
    query_string_behavior = "all"
  }
}
