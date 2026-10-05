provider "aws" {
  region = "us-east-1" # CloudFront expects ACM resources in us-east-1 region only

  default_tags {
    tags = {
      "Project"     = "AWS Educate TPET"
      "Service"     = "shared"
      "Environment" = "shared"
      "Repository"  = "aws-educate-tw/aws-educate-tpet-backend"
      "ManagedBy"   = "terraform"
    }
  }
}
