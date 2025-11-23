provider "aws" {
  region = var.aws_region
  profile = "dev-local"
  default_tags {
    tags = {
      "Terraform"   = "true",
      "Environment" = var.environment,
      "Project"     = "AWS Educate TPET"
    }
  }
}
