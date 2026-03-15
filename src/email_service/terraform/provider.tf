provider "aws" {
  region = var.aws_region
  profile = "tpet-aws-educate"

  default_tags {
    tags = {
      "Terraform"   = "true",
      "Environment" = var.environment,
      "Project"     = "AWS Educate TPET"
    }
  }
}
