terraform {
  backend "s3" {
    bucket         = "terraform-state-20240618152116874600000001"
    region         = "us-west-2"
    key            = "cloudfront_for_apis/global/terraform.tfstate"
    dynamodb_table = "terraform-locks"
  }
}
