provider "aws" {
  region = "us-eest-1"
  default_tags {
    tags = {
      Environment = var.environment
      Terraform   = "true"
      Service     = "file-service"
    }

  }
}

data "aws_region" "current" {}
