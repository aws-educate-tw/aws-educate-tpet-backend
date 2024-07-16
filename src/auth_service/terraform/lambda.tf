data "aws_ecr_authorization_token" "token" {
}

data "aws_caller_identity" "this" {}

resource "random_string" "this" {
  length  = 4
  special = false
  lower   = true
  upper   = false
}

locals {
  source_path                                       = "${path.module}/.."
  login_function_name_and_ecr_repo_name             = "${var.environment}-${var.service_underscore}-login-${random_string.this.result}"
  lambda_authorizer_function_name_and_ecr_repo_name = "${var.environment}-${var.service_underscore}-lambda_authorizer-${random_string.this.result}"
  path_include                                      = ["**"]
  path_exclude                                      = ["**/__pycache__/**"]
  files_include                                     = setunion([for f in local.path_include : fileset(local.source_path, f)]...)
  files_exclude                                     = setunion([for f in local.path_exclude : fileset(local.source_path, f)]...)
  files                                             = sort(setsubtract(local.files_include, local.files_exclude))
  dir_sha                                           = sha1(join("", [for f in local.files : filesha1("${local.source_path}/${f}")]))
}

provider "docker" {
  registry_auth {
    address  = format("%v.dkr.ecr.%v.amazonaws.com", data.aws_caller_identity.this.account_id, var.aws_region)
    username = data.aws_ecr_authorization_token.token.user_name
    password = data.aws_ecr_authorization_token.token.password
  }
}

####################################
####################################
####################################
# POST /login ######################
####################################
####################################
####################################

module "login_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.0"

  function_name  = local.login_function_name_and_ecr_repo_name
  description    = "AWS Educate TPET ${var.service_hyphen} in ${var.environment}: POST /login"
  create_package = false
  timeout        = 300

  ##################
  # Container Image
  ##################
  package_type  = "Image"
  architectures = ["x86_64"] # or ["arm64"]
  image_uri     = module.login_docker_image.image_uri

  publish = true # Whether to publish creation/change as new Lambda Function Version.


  environment_variables = {
    "ENVIRONMENT"    = var.environment,
    "SERVICE"        = var.service_underscore
    "DYNAMODB_TABLE" = var.dynamodb_table
  }

  allowed_triggers = {
    AllowExecutionFromAPIGateway = {
      service    = "apigateway"
      source_arn = "${module.api_gateway.api_execution_arn}/*/*"
    }
  }

  tags = {
    "Terraform"   = "true",
    "Environment" = var.environment,
    "Service"     = var.service_underscore
  }
  ######################
  # Additional policies
  ######################

  attach_policy_statements = true
  policy_statements = {
    dynamodb_crud = {
      effect = "Allow",
      actions = [
        "dynamodb:BatchGetItem",
        "dynamodb:BatchWriteItem",
        "dynamodb:DeleteItem",
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:UpdateItem"
      ],
      resources = [
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/${var.dynamodb_table}"
      ]
    }
  }
}

module "login_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.7.0"

  create_ecr_repo      = true
  keep_remotely        = true
  use_image_tag        = false
  image_tag_mutability = "MUTABLE"
  ecr_repo             = local.login_function_name_and_ecr_repo_name
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

  # docker_campaign_path = "${local.source_path}/path/to/Dockercampaign" # set `docker_campaign_path` If your Dockercampaign is not in `source_path`
  source_path = "${local.source_path}/login/" # Remember to change
  triggers = {
    dir_sha = local.dir_sha
  }

}


####################################
####################################
####################################
# Lambda Authorizer ################
####################################
####################################
####################################

module "lambda_authorizer_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.0"

  function_name  = local.lambda_authorizer_function_name_and_ecr_repo_name
  description    = "AWS Educate TPET ${var.service_hyphen} in ${var.environment}: POST /lambda_authorizer"
  create_package = false
  timeout        = 300

  ##################
  # Container Image
  ##################
  package_type  = "Image"
  architectures = ["x86_64"] # or ["arm64"]
  image_uri     = module.lambda_authorizer_docker_image.image_uri

  publish = true # Whether to publish creation/change as new Lambda Function Version.


  environment_variables = {
    "ENVIRONMENT"    = var.environment,
    "SERVICE"        = var.service_underscore
    "DYNAMODB_TABLE" = var.dynamodb_table
  }

  allowed_triggers = {
    AllowExecutionFromAPIGateway = {
      service    = "apigateway"
      source_arn = "${module.api_gateway.api_execution_arn}/*/*"
    }
  }

  tags = {
    "Terraform"   = "true",
    "Environment" = var.environment,
    "Service"     = var.service_underscore
  }
  ######################
  # Additional policies
  ######################

  attach_policy_statements = true
  policy_statements = {
    dynamodb_crud = {
      effect = "Allow",
      actions = [
        "dynamodb:BatchGetItem",
        "dynamodb:BatchWriteItem",
        "dynamodb:DeleteItem",
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:UpdateItem"
      ],
      resources = [
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/${var.dynamodb_table}"
      ]
    }
  }
}

module "lambda_authorizer_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.7.0"

  create_ecr_repo      = true
  keep_remotely        = true
  use_image_tag        = false
  image_tag_mutability = "MUTABLE"
  ecr_repo             = local.lambda_authorizer_function_name_and_ecr_repo_name
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

  # docker_campaign_path = "${local.source_path}/path/to/Dockercampaign" # set `docker_campaign_path` If your Dockercampaign is not in `source_path`
  source_path = "${local.source_path}/lambda_authorizer/" # Remember to change
  triggers = {
    dir_sha = local.dir_sha
  }

}
