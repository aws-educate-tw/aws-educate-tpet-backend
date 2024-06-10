terraform {
  backend "s3" {
    bucket         = "poc-terraform-state-20240610102132009600000001"
    key            = "poc/terraform.tfstate"
    region         = "ap-northeast-1"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}
