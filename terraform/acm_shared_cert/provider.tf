provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      "Project"     = "AWS Educate TPET"
      "Service"     = "shared"
      "Environment" = var.environment
      "Repository"  = "aws-educate-tw/aws-educate-tpet-backend"
      "ManagedBy"   = "terraform"
    }
  }
}
