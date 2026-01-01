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
  host = "npipe:////./pipe/docker_engine"

  registry_auth {
    address  = data.aws_ecr_authorization_token.token.proxy_endpoint
    username = data.aws_ecr_authorization_token.token.user_name
    password = data.aws_ecr_authorization_token.token.password
  }
}
