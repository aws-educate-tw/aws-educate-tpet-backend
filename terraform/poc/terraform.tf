terraform {
  backend "s3" {
    bucket         = "terraform-state-20240610123048790400000001"
    key            = "poc/terraform.tfstate"
    region         = "ap-northeast-1"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}
