provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      "Terraform"   = "true",
      "Environment" = var.environment,
      "Project"     = "AWS Educate TPET"
      "Service"     = "acm_shared_cert"
    }
  }
}
