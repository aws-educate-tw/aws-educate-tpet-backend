resource "aws_cloudfront_distribution" "api_distribution" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "CloudFront distribution for multiple API Gateways"
  default_root_object = ""

  aliases = [var.domain_name]

  viewer_certificate {
    acm_certificate_arn      = var.acm_certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  dynamic "origin" {
    for_each = var.api_gateway_origins
    content {
      domain_name = origin.value.domain_name
      origin_id   = origin.value.domain_name

      custom_origin_config {
        http_port              = 80
        https_port             = 443
        origin_protocol_policy = "https-only"
        origin_ssl_protocols   = ["TLSv1.2"]
      }
    }
  }

  dynamic "cache_behavior" {
    for_each = var.api_gateway_origins
    content {
      path_pattern           = cache_behavior.value.path_pattern
      target_origin_id       = cache_behavior.value.domain_name
      viewer_protocol_policy = "redirect-to-https"

      allowed_methods = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
      cached_methods  = ["GET", "HEAD"]

      forwarded_values {
        query_string = true
        headers      = ["Origin", "Access-Control-Request-Headers", "Access-Control-Request-Method"]
      }

      min_ttl     = 0
      default_ttl = 3600
      max_ttl     = 86400

      lambda_function_association {
        event_type = "origin-response"
        lambda_arn = var.simple_cors_lambda_arn
      }
    }
  }

  default_cache_behavior {
    target_origin_id       = var.api_gateway_origins[0].domain_name
    viewer_protocol_policy = "redirect-to-https"

    allowed_methods = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods  = ["GET", "HEAD"]

    forwarded_values {
      cookies {
        forward = "none"
      }
      query_string = true
      headers      = ["Origin", "Access-Control-Request-Headers", "Access-Control-Request-Method"]
    }

    min_ttl     = 0
    default_ttl = 3600
    max_ttl     = 86400

  }

  logging_config {
    include_cookies = false
    bucket          = "aws-eudcate-tpet-cloudfront-logging-bucket.s3.amazonaws.com"
    prefix          = "cloudfront/"
  }
}
