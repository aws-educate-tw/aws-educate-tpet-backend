terraform {
  backend "s3" {
    bucket         = "terraform-state-20240610095057872800000001"
    key            = "dev/terraform.tfstate"
    region         = "ap-northeast-1"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}
