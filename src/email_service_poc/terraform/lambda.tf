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
  source_path                                   = "${path.module}/.."
  list_runs_poc_function_name_and_ecr_repo_name = "${var.environment}-${var.service_underscore}-list_runs_poc-${random_string.this.result}"

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

# This is for POC !!!

####################################
####################################
####################################
# GET /runs ########################
####################################
####################################
####################################

module "list_runs_poc_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.0"

  function_name  = local.list_runs_poc_function_name_and_ecr_repo_name                       # Remember to change
  description    = "AWS Educate TPET ${var.service_hyphen} in ${var.environment}: GET /runs" # Remember to change
  create_package = false
  timeout        = 30

  ##################
  # Container Image
  ##################
  package_type  = "Image"
  architectures = [var.lambda_architecture]
  image_uri     = module.list_runs_poc_docker_image.image_uri # Remember to change

  publish = true # Whether to publish creation/change as new Lambda Function Version.


  environment_variables = {
    "ENVIRONMENT"   = var.environment,
    "SERVICE"       = var.service_underscore
    "DATABASE_NAME" = var.database_name,
    "CLUSTER_ARN"   = var.cluster_arn,
    "SECRET_ARN"    = var.secret_arn,
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
    # "Prewarm"     = "true"
  }
  ######################
  # Additional policies
  ######################

  attach_policy_statements = true
  policy_statements = {
    rds_data_access = {
      effect = "Allow",
      actions = [
        "rds-data:ExecuteStatement",
        "rds-data:BatchExecuteStatement",
        "rds-data:BeginTransaction",
        "rds-data:CommitTransaction",
        "rds-data:RollbackTransaction"
      ],
      resources = [
        var.cluster_arn
      ]
    },
    secrets_manager_access = {
      effect = "Allow",
      actions = [
        "secretsmanager:GetSecretValue"
      ],
      resources = [
        var.secret_arn
      ]
    }
  }
}

module "list_runs_poc_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.7.0"

  create_ecr_repo      = true
  keep_remotely        = true
  use_image_tag        = false
  image_tag_mutability = "MUTABLE"
  ecr_repo             = local.list_runs_poc_function_name_and_ecr_repo_name # Remember to change
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

  # docker_file_path = "${local.source_path}/path/to/Dockerfile" # set `docker_file_path` If your Dockerfile is not in `source_path`
  source_path = "${local.source_path}/list_runs/" # Remember to change
  triggers = {
    dir_sha = local.dir_sha
  }

}
