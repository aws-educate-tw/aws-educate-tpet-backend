terraform {
  required_version = ">= 1.8.0, <= 1.13.4"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.54.0"
    }
  }
}
