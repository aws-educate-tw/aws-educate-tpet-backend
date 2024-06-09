provider "aws" {
  region = "ap-northeast-1"
}

data "aws_region" "current" {}
