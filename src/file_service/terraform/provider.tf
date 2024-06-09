provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Environment = var.environment
      Terraform   = "true"
      Service     = "file-service"
    }

  }
}

data "aws_region" "current" {}
