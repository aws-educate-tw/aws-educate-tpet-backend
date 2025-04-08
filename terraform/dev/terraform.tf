terraform {
  backend "s3" {
    bucket         = "tpet-terraform-state-20250401155336893000000001"
    key            = "dev/terraform.tfstate"
    region         = "us-west-2"
    dynamodb_table = "tpet-terraform-locks"
    encrypt        = true
  }
}
