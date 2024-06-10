resource "aws_s3_bucket" "cloudfront_logging" {
  bucket = "aws-educate-tpet-cloudfront-logs"

  tags = {
    Name      = "cloudfront-logs"
    Terraform = "true"
  }
}
