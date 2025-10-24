terraform {
  backend "s3" {
    bucket         = "tpet-terraform-state-20250401155336893000000001"
    region         = "us-west-2"
    key            = "cloudfront_for_apis/global/terraform.tfstate"
    dynamodb_table = "terraform-locks"
  }
}
