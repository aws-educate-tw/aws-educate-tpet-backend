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
  rsvp_update_function_name_and_ecr_repo_name       = "${var.environment}-${var.service_underscore}-rsvp_update-${random_string.this.result}"
  rsvp_status_query_function_name_and_ecr_repo_name = "${var.environment}-${var.service_underscore}-rsvp_status_query-${random_string.this.result}"
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
# PUT /api/rsvp ####################
####################################
####################################
####################################

module "rsvp_update_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.0"

  function_name  = local.rsvp_update_function_name_and_ecr_repo_name
  description    = "AWS Educate TPET ${var.service_hyphen} in ${var.environment}: PUT /api/rsvp"
  create_package = false
  timeout        = 30

  ##################
  # Container Image
  ##################
  package_type  = "Image"
  architectures = [var.lambda_architecture]
  image_uri     = module.rsvp_update_docker_image.image_uri

  publish = true # Whether to publish creation/change as new Lambda Function Version.

  environment_variables = {
    "ENVIRONMENT"            = var.environment,
    "SERVICE"                = var.service_underscore,
    "DYNAMODB_TABLE"         = var.dynamodb_table,
    "SYNC_AURORA_LAMBDA_ARN" = module.sync_aurora_lambda.lambda_function_arn
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
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/${var.dynamodb_table}",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/${var.dynamodb_table}/index/sk-run_id-gsi"
      ]
    }
    scheduler_manage = {
      effect = "Allow",
      actions = [
        "scheduler:CreateSchedule",
        "scheduler:UpdateSchedule",
        "scheduler:DeleteSchedule",
        "scheduler:GetSchedule"
      ],
      resources = [
        "arn:aws:scheduler:${var.aws_region}:${data.aws_caller_identity.this.account_id}:schedule/default/*"
      ]
    }
    scheduler_pass_role = {
      effect = "Allow",
      actions = [
        "iam:PassRole"
      ],
      resources = [
        aws_iam_role.eventbridge_scheduler_role.arn
      ]
    }
  }
}

module "rsvp_update_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.7.0"

  create_ecr_repo      = true
  keep_remotely        = true
  use_image_tag        = false
  image_tag_mutability = "MUTABLE"
  ecr_repo             = local.rsvp_update_function_name_and_ecr_repo_name
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
  source_path = "${local.source_path}/rsvp_update/" # Remember to change
  triggers = {
    dir_sha = local.dir_sha
  }
}

####################################
####################################
####################################
# GET /api/rsvp ####################
####################################
####################################
####################################

module "rsvp_status_query_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.0"

  function_name  = local.rsvp_status_query_function_name_and_ecr_repo_name
  description    = "AWS Educate TPET ${var.service_hyphen} in ${var.environment}: GET /api/rsvp"
  create_package = false
  timeout        = 30

  ##################
  # Container Image
  ##################
  package_type  = "Image"
  architectures = [var.lambda_architecture]
  image_uri     = module.rsvp_status_query_docker_image.image_uri

  publish = true # Whether to publish creation/change as new Lambda Function Version.

  environment_variables = {
    "ENVIRONMENT"    = var.environment,
    "SERVICE"        = var.service_underscore,
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
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/${var.dynamodb_table}",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/${var.dynamodb_table}/index/sk-run_id-gsi"
      ]
    }
  }
}

module "rsvp_status_query_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.7.0"

  create_ecr_repo      = true
  keep_remotely        = true
  use_image_tag        = false
  image_tag_mutability = "MUTABLE"
  ecr_repo             = local.rsvp_status_query_function_name_and_ecr_repo_name
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
  source_path = "${local.source_path}/rsvp_status_query/" # Remember to change
  triggers = {
    dir_sha = local.dir_sha
  }
}

####################################
####################################
####################################
# Sync Aurora (Final Flush) ########
####################################
####################################
####################################

module "sync_aurora_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.0"

  function_name  = "${var.environment}-${var.service_underscore}-sync_aurora-${random_string.this.result}"
  description    = "AWS Educate TPET ${var.service_hyphen} in ${var.environment}: Sync Aurora FINAL_FLUSH"
  create_package = false
  timeout        = 300
  memory_size    = 512

  ##################
  # Container Image
  ##################
  package_type  = "Image"
  architectures = [var.lambda_architecture]
  image_uri     = module.sync_aurora_docker_image.image_uri

  publish = true # Whether to publish creation/change as new Lambda Function Version.

  environment_variables = {
    "ENVIRONMENT"    = var.environment,
    "SERVICE"        = var.service_underscore,
    "DYNAMODB_TABLE" = var.dynamodb_table
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
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/${var.dynamodb_table}",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/${var.dynamodb_table}/index/sk-run_id-gsi"
      ]
    }
  }
}

module "sync_aurora_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.7.0"

  create_ecr_repo      = true
  keep_remotely        = true
  use_image_tag        = false
  image_tag_mutability = "MUTABLE"
  ecr_repo             = "${var.environment}-${var.service_underscore}-sync_aurora-${random_string.this.result}"
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
  source_path = "${local.source_path}/sync_aurora/" # Remember to change
  triggers = {
    dir_sha = local.dir_sha
  }
}
