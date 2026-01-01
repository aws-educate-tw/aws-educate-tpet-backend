data "aws_ecr_authorization_token" "token" {}

data "aws_caller_identity" "this" {}

locals {
  source_path  = "${path.module}/.."
  function_name = "onboarding-aaron"
  ecr_repo_name = "onboarding-aaron"
  path_include  = ["**"]
  path_exclude  = ["**/__pycache__/**"]
  files_include = setunion([for f in local.path_include : fileset(local.source_path, f)]...)
  files_exclude = setunion([for f in local.path_exclude : fileset(local.source_path, f)]...)
  files         = sort(setsubtract(local.files_include, local.files_exclude))
  dir_sha       = sha1(join("", [for f in local.files : filesha1("${local.source_path}/${f}")]))
}

provider "docker" {
  registry_auth {
    address  = format("%v.dkr.ecr.%v.amazonaws.com", data.aws_caller_identity.this.account_id, var.aws_region)
    username = data.aws_ecr_authorization_token.token.user_name
    password = data.aws_ecr_authorization_token.token.password
  }
}

module "onboarding_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.0"

  function_name  = local.function_name
  description    = "AWS Educate TPET onboarding-aaron in ${var.environment}: GET {{base_url}}/onboarding/aaron"
  create_package = false
  timeout        = 10

  ##################
  # Container Image
  ##################
  package_type  = "Image"
  architectures = [var.lambda_architecture]
  image_uri     = module.onboarding_docker_image.image_uri

  publish = true

  allowed_triggers = {
    AllowExecutionFromAPIGateway = {
      service    = "apigateway"
      source_arn = "${aws_apigatewayv2_api.onboarding.execution_arn}/*/*"
    }
  }

  tags = {
    "Terraform"   = "true"
    "Environment" = var.environment
    "Service"     = "onboarding-aaron"
  }
}

module "onboarding_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.7.0"

  create_ecr_repo      = true
  keep_remotely        = true
  use_image_tag        = false
  image_tag_mutability = "MUTABLE"
  ecr_repo             = local.ecr_repo_name
  ecr_repo_lifecycle_policy = jsonencode({
    "rules" : [
      {
        "rulePriority" : 1,
        "description" : "Keep only the last 10 images",
        "selection" : {
          "tagStatus" : "any",
          "countType" : "imageCountMoreThan",
          "countNumber" : 10
        },
        "action" : {
          "type" : "expire"
        }
      }
    ]
  })

  source_path = "${local.source_path}/get_info/"
  triggers = {
    dir_sha = local.dir_sha
  }
}