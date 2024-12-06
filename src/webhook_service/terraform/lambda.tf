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
  source_path = "${path.module}/.."
  # upload_multiple_file_function_name_and_ecr_repo_name = "${var.environment}-${var.service_underscore}-upload_multiple_file-${random_string.this.result}"
  # list_files_function_name_and_ecr_repo_name           = "${var.environment}-${var.service_underscore}-list_files-${random_string.this.result}"
  # get_file_function_name_and_ecr_repo_name             = "${var.environment}-${var.service_underscore}-get_file-${random_string.this.result}"
  get_webhook_function_name_and_ecr_repo_name     = "${var.environment}-${var.service_underscore}-get_webhook-${random_string.this.result}"
  save_webhook_function_name_and_ecr_repo_name    = "${var.environment}-${var.service_underscore}-save_webhook-${random_string.this.result}"
  trigger_webhook_function_name_and_ecr_repo_name = "${var.environment}-${var.service_underscore}-trigger_webhook-${random_string.this.result}"
  path_include                                    = ["**"]
  path_exclude                                    = ["**/__pycache__/**"]
  files_include                                   = setunion([for f in local.path_include : fileset(local.source_path, f)]...)
  files_exclude                                   = setunion([for f in local.path_exclude : fileset(local.source_path, f)]...)
  files                                           = sort(setsubtract(local.files_include, local.files_exclude))
  dir_sha                                         = sha1(join("", [for f in local.files : filesha1("${local.source_path}/${f}")]))
}

provider "docker" {
  host = var.docker_host

  registry_auth {
    address  = format("%v.dkr.ecr.%v.amazonaws.com", data.aws_caller_identity.this.account_id, var.aws_region)
    username = data.aws_ecr_authorization_token.token.user_name
    password = data.aws_ecr_authorization_token.token.password
  }
}
####################################
####################################
####################################
# GET /webhooks/{webhook_id} #######
####################################
####################################
####################################

module "get_webhook_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.0"

  function_name  = local.get_webhook_function_name_and_ecr_repo_name
  description    = "AWS Educate TPET ${var.service_hyphen} in ${var.environment}: GET /webhook/{webhook_id} "
  create_package = false
  timeout        = 30

  ##################
  # Container Image
  ##################
  package_type = "Image"
  # architectures = ["x86_64"] # or ["arm64"]
  architectures = ["arm64"]
  # image_uri     = "public.ecr.aws/lambda/python:3.8"
  # image_uri     = module.list_emails_docker_image.image_uri
  image_uri = module.get_webhook_docker_image.image_uri

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
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/${var.dynamodb_table}"
      ]
    },
    s3_crud = {
      effect = "Allow",
      actions = [
        "s3:ListBucket",
        "s3:GetBucketLocation",
        "s3:CreateBucket",
        "s3:DeleteBucket",
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucketMultipartUploads",
        "s3:ListMultipartUploadParts",
        "s3:AbortMultipartUpload"
      ],
      resources = [
        "arn:aws:s3:::${var.environment}-aws-educate-tpet-storage",
        "arn:aws:s3:::${var.environment}-aws-educate-tpet-storage/*"
      ]
    }
  }

}

module "get_webhook_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.7.0"

  create_ecr_repo      = true
  keep_remotely        = true
  use_image_tag        = false
  image_tag_mutability = "MUTABLE"
  ecr_repo             = local.get_webhook_function_name_and_ecr_repo_name
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

  source_path = "${local.source_path}/get_webhook/"
  triggers = {
    dir_sha = local.dir_sha
  }
}


####################################
####################################
####################################
# POST /webhook ####################
####################################
####################################
####################################

module "save_webhook_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.0"

  function_name  = local.save_webhook_function_name_and_ecr_repo_name
  description    = "AWS Educate TPET ${var.service_hyphen} in ${var.environment}: POST /webhook"
  create_package = false
  timeout        = 30

  ##################
  # Container Image
  ##################
  package_type = "Image"
  # architectures = ["x86_64"] # or ["arm64"]
  architectures = ["arm64"]
  # image_uri     = "public.ecr.aws/lambda/python:3.8"
  # image_uri     = module.list_emails_docker_image.image_uri
  image_uri = module.save_webhook_docker_image.image_uri

  publish = true # Whether to publish creation/change as new Lambda Function Version.

  environment_variables = {
    "ENVIRONMENT"                  = var.environment,
    "SERVICE"                      = var.service_underscore,
    "DYNAMODB_TABLE"               = var.dynamodb_table
    "TRIGGER_WEBHOOK_API_ENDPOINT" = var.trigger_webhook_api_endpoint
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
    },
    s3_crud = {
      effect = "Allow",
      actions = [
        "s3:ListBucket",
        "s3:GetBucketLocation",
        "s3:CreateBucket",
        "s3:DeleteBucket",
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucketMultipartUploads",
        "s3:ListMultipartUploadParts",
        "s3:AbortMultipartUpload"
      ],
      resources = [
        "arn:aws:s3:::${var.environment}-aws-educate-tpet-storage",
        "arn:aws:s3:::${var.environment}-aws-educate-tpet-storage/*"
      ]
    }
  }

}

module "save_webhook_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.7.0"

  create_ecr_repo      = true
  keep_remotely        = true
  use_image_tag        = false
  image_tag_mutability = "MUTABLE"
  ecr_repo             = local.save_webhook_function_name_and_ecr_repo_name
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

  source_path = "${local.source_path}/save_webhook/"
  triggers = {
    dir_sha = local.dir_sha
  }
}


####################################
####################################
####################################
# POST /trigger-webhook/{webhook_id}
####################################
####################################
####################################

module "trigger_webhook_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.0"

  function_name  = local.trigger_webhook_function_name_and_ecr_repo_name
  description    = "AWS Educate TPET ${var.service_hyphen} in ${var.environment}: POST /trigger-webhook/{webhook_id}"
  create_package = false
  timeout        = 30

  ##################
  # Container Image
  ##################
  package_type = "Image"
  # architectures = ["x86_64"] # or ["arm64"]
  architectures = ["arm64"]
  # image_uri     = "public.ecr.aws/lambda/python:3.8"
  # image_uri     = module.list_emails_docker_image.image_uri
  image_uri = module.trigger_webhook_docker_image.image_uri

  publish = true # Whether to publish creation/change as new Lambda Function Version.

  environment_variables = {
    "ENVIRONMENT"             = var.environment,
    "SERVICE"                 = var.service_underscore,
    "DYNAMODB_TABLE"          = var.dynamodb_table
    "SEND_EMAIL_API_ENDPOINT" = var.send_email_api_endpoint
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
    },
    s3_crud = {
      effect = "Allow",
      actions = [
        "s3:ListBucket",
        "s3:GetBucketLocation",
        "s3:CreateBucket",
        "s3:DeleteBucket",
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucketMultipartUploads",
        "s3:ListMultipartUploadParts",
        "s3:AbortMultipartUpload"
      ],
      resources = [
        "arn:aws:s3:::${var.environment}-aws-educate-tpet-storage",
        "arn:aws:s3:::${var.environment}-aws-educate-tpet-storage/*"
      ]
    }
  }

}

module "trigger_webhook_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.7.0"

  create_ecr_repo      = true
  keep_remotely        = true
  use_image_tag        = false
  image_tag_mutability = "MUTABLE"
  ecr_repo             = local.trigger_webhook_function_name_and_ecr_repo_name
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

  source_path = "${local.source_path}/trigger_webhook/"
  triggers = {
    dir_sha = local.dir_sha
  }
}
