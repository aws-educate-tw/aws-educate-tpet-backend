resource "aws_s3_bucket" "cloudfront_logging" {
  bucket = "aws-educate-tpet-cloudfront-logs"

  tags = {
    Name      = "cloudfront-logs"
    Terraform = "true"
  }
}

resource "aws_s3_bucket_policy" "cloudfront_logging_policy" {
  bucket = aws_s3_bucket.cloudfront_logging.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "cloudfront.amazonaws.com"
        },
        Action   = "s3:PutObject",
        Resource = "${aws_s3_bucket.cloudfront_logging.arn}/*",
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = "arn:aws:cloudfront::${data.aws_caller_identity.current.account_id}:distribution/*"
          }
        }
      }
    ]
  })
}

data "aws_caller_identity" "current" {}
