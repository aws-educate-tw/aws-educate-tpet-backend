provider "aws" {
  region = "us-east-1" # CloudFront expects ACM resources in us-east-1 region only
  default_tags {
    tags = {
      "Terraform"   = "true",
      "Environment" = "global",
      "Project"     = "AWS Educate TPET"
      "Service"     = "cloudfront_for_apis"
    }
  }
}
