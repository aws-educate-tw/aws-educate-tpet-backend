provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      "Terraform"   = "true"
      "Environment" = var.environment
      "Project"     = "AWS Educate TPET"
    }
  }
}

provider "docker" {
  registry_auth {
    address  = format("%v.dkr.ecr.%v.amazonaws.com", data.aws_caller_identity.this.account_id, var.aws_region)
    username = data.aws_ecr_authorization_token.token.user_name
    password = data.aws_ecr_authorization_token.token.password
  }
}
