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
  source_path                                           = "${path.module}/.."
  update_rsvp_function_name_and_ecr_repo_name           = "${var.environment}-${var.service_underscore}-update_rsvp-${random_string.this.result}"
  get_rsvp_status_function_name_and_ecr_repo_name     = "${var.environment}-${var.service_underscore}-get_rsvp_status-${random_string.this.result}"
  verify_campaign_function_name_and_ecr_repo_name   = "${var.environment}-${var.service_underscore}-verify_campaign-${random_string.this.result}"
  upsert_run_configuration_function_name_and_ecr_repo_name  = "${var.environment}-${var.service_underscore}-upsert_run_configuration-${random_string.this.result}"
  import_participant_function_name_and_ecr_repo_name = "${var.environment}-${var.service_underscore}-import_participant-${random_string.this.result}"
  list_campaigns_function_name_and_ecr_repo_name   = "${var.environment}-${var.service_underscore}-list_campaigns-${random_string.this.result}"
  get_campaign_function_name_and_ecr_repo_name          = "${var.environment}-${var.service_underscore}-get_campaign-${random_string.this.result}"
  create_campaign_function_name_and_ecr_repo_name       = "${var.environment}-${var.service_underscore}-create_campaign-${random_string.this.result}"
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
# PUT /rsvp/{run_id_participant_id} ########################
####################################
####################################
####################################

module "update_rsvp_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.0"

  function_name  = local.update_rsvp_function_name_and_ecr_repo_name
  description    = "AWS Educate TPET ${var.service_hyphen} in ${var.environment}: PUT /rsvp/{run_id_participant_id}"
  create_package = false
  timeout        = 30

  ##################
  # Container Image
  ##################
  package_type  = "Image"
  architectures = [var.lambda_architecture]
  image_uri     = module.update_rsvp_docker_image.image_uri

  publish = true # Whether to publish creation/change as new Lambda Function Version.

  environment_variables = {
    "ENVIRONMENT"     = var.environment,
    "SERVICE"         = var.service_underscore,
    "DYNAMODB_TABLE"  = "participant",
    "PARTICIPANTS_TABLE" = "participant",
    "RUNS_CAMPAIGNS_MAPPING_TABLE" = "campaign_run",
    "CAMPAIGNS_TABLE" = "Campaigns"
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
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/participant",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/participant/index/participant-campaign_participant_uniq_handle-created_at-gsi",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/Campaigns",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/campaign_run"
      ]
    }
  }
}

module "update_rsvp_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.7.0"

  create_ecr_repo      = true
  keep_remotely        = true
  keep_locally         = true
  use_image_tag        = false
  image_tag_mutability = "MUTABLE"
  ecr_repo             = local.update_rsvp_function_name_and_ecr_repo_name
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
  source_path = "${local.source_path}/update_rsvp/" # Remember to change
  triggers = {
    dir_sha = local.dir_sha
  }
}

####################################
####################################
####################################
# GET /rsvp/{run_id_participant_id}/status ########################
####################################
####################################
####################################

module "get_rsvp_status_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.0"

  function_name  = local.get_rsvp_status_function_name_and_ecr_repo_name
  description    = "AWS Educate TPET ${var.service_hyphen} in ${var.environment}: GET /rsvp/{run_id_participant_id}/status"
  create_package = false
  timeout        = 30

  ##################
  # Container Image
  ##################
  package_type  = "Image"
  architectures = [var.lambda_architecture]
  image_uri     = module.get_rsvp_status_docker_image.image_uri

  publish = true # Whether to publish creation/change as new Lambda Function Version.

  environment_variables = {
    "ENVIRONMENT"     = var.environment,
    "SERVICE"         = var.service_underscore,
    "DYNAMODB_TABLE"  = "participant",
    "PARTICIPANTS_TABLE" = "participant",
    "RUNS_CAMPAIGNS_MAPPING_TABLE" = "campaign_run",
    "CAMPAIGNS_TABLE" = "Campaigns"
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
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/participant",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/participant/index/participant-campaign_participant_uniq_handle-created_at-gsi",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/Campaigns",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/campaign_run"
      ]
    }
  }
}

module "get_rsvp_status_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.7.0"

  create_ecr_repo      = true
  keep_remotely        = true
  keep_locally         = true
  use_image_tag        = false
  image_tag_mutability = "MUTABLE"
  ecr_repo             = local.get_rsvp_status_function_name_and_ecr_repo_name
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
  source_path = "${local.source_path}/get_rsvp_status/" # Remember to change
  triggers = {
    dir_sha = local.dir_sha
  }
}

####################################
####################################
####################################
# GET /internal/campaign/{campaign_id}/check
####################################
####################################
####################################

module "verify_campaign_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.0"

  function_name  = local.verify_campaign_function_name_and_ecr_repo_name
  description    = "AWS Educate TPET ${var.service_hyphen} in ${var.environment}: GET /internal/campaign/{campaign_id}/check"
  create_package = false
  timeout        = 30

  ##################
  # Container Image
  ##################
  package_type  = "Image"
  architectures = [var.lambda_architecture]
  image_uri     = module.verify_campaign_docker_image.image_uri

  publish = true # Whether to publish creation/change as new Lambda Function Version.

  environment_variables = {
    "ENVIRONMENT"     = var.environment,
    "SERVICE"         = var.service_underscore,
    "DYNAMODB_TABLE"  = "participant",
    "PARTICIPANTS_TABLE" = "participant",
    "RUNS_CAMPAIGNS_MAPPING_TABLE" = "campaign_run",
    "CAMPAIGNS_TABLE" = "Campaigns"
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
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/participant",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/participant/index/participant-campaign_participant_uniq_handle-created_at-gsi",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/Campaigns",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/campaign_run"
      ]
    }
  }
}

module "verify_campaign_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.7.0"

  create_ecr_repo      = true
  keep_remotely        = true
  keep_locally         = true
  use_image_tag        = false
  image_tag_mutability = "MUTABLE"
  ecr_repo             = local.verify_campaign_function_name_and_ecr_repo_name
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
  source_path = "${local.source_path}/verify_campaign/" # Remember to change
  triggers = {
    dir_sha = local.dir_sha
  }
}

####################################
####################################
####################################
# PUT /internal/campaign-runs/{campaign_id_run_id}
####################################
####################################
####################################

module "upsert_run_configuration_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.0"

  function_name  = local.upsert_run_configuration_function_name_and_ecr_repo_name
  description    = "AWS Educate TPET ${var.service_hyphen} in ${var.environment}: PUT /internal/campaign-runs/{campaign_id_run_id}"
  create_package = false
  timeout        = 30

  ##################
  # Container Image
  ##################
  package_type  = "Image"
  architectures = [var.lambda_architecture]
  image_uri     = module.upsert_run_configuration_docker_image.image_uri

  publish = true # Whether to publish creation/change as new Lambda Function Version.

  environment_variables = {
    "ENVIRONMENT"     = var.environment,
    "SERVICE"         = var.service_underscore,
    "DYNAMODB_TABLE"  = "participant",
    "PARTICIPANTS_TABLE" = "participant",
    "RUNS_CAMPAIGNS_MAPPING_TABLE" = "campaign_run",
    "CAMPAIGNS_TABLE" = "Campaigns"
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
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/participant",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/participant/index/participant-campaign_participant_uniq_handle-created_at-gsi",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/Campaigns",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/campaign_run"
      ]
    }
  }
}

module "upsert_run_configuration_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.7.0"

  create_ecr_repo      = true
  keep_remotely        = true
  keep_locally         = true
  use_image_tag        = false
  image_tag_mutability = "MUTABLE"
  ecr_repo             = local.upsert_run_configuration_function_name_and_ecr_repo_name
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
  source_path = "${local.source_path}/upsert_run_configuration/" # Remember to change
  triggers = {
    dir_sha = local.dir_sha
  }
}

####################################
####################################
####################################
# POST /internal/runs/{run_id}/participants/
####################################
####################################
####################################

module "import_participant_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.0"

  function_name  = local.import_participant_function_name_and_ecr_repo_name
  description    = "AWS Educate TPET ${var.service_hyphen} in ${var.environment}: POST /internal/runs/{run_id}/participants/"
  create_package = false
  timeout        = 30

  ##################
  # Container Image
  ##################
  package_type  = "Image"
  architectures = [var.lambda_architecture]
  image_uri     = module.import_participant_docker_image.image_uri

  publish = true # Whether to publish creation/change as new Lambda Function Version.

  environment_variables = {
    "ENVIRONMENT"     = var.environment,
    "SERVICE"         = var.service_underscore,
    "DYNAMODB_TABLE"  = "participant",
    "PARTICIPANTS_TABLE" = "participant",
    "RUNS_CAMPAIGNS_MAPPING_TABLE" = "campaign_run",
    "CAMPAIGNS_TABLE" = "Campaigns"
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
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/participant",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/participant/index/participant-campaign_participant_uniq_handle-created_at-gsi",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/Campaigns",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/campaign_run"
      ]
    }
  }
}

module "import_participant_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.7.0"

  create_ecr_repo      = true
  keep_remotely        = true
  keep_locally         = true
  use_image_tag        = false
  image_tag_mutability = "MUTABLE"
  ecr_repo             = local.import_participant_function_name_and_ecr_repo_name
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
  source_path = "${local.source_path}/import_participant/" # Remember to change
  triggers = {
    dir_sha = local.dir_sha
  }
}

####################################
####################################
####################################
# GET /campaigns
####################################
####################################
####################################

module "list_campaigns_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.0"

  function_name  = local.list_campaigns_function_name_and_ecr_repo_name
  description    = "AWS Educate TPET ${var.service_hyphen} in ${var.environment}: GET /campaigns"
  create_package = false
  timeout        = 30

  ##################
  # Container Image
  ##################
  package_type  = "Image"
  architectures = [var.lambda_architecture]
  image_uri     = module.list_campaigns_docker_image.image_uri

  publish = true # Whether to publish creation/change as new Lambda Function Version.

  environment_variables = {
    "ENVIRONMENT"     = var.environment,
    "SERVICE"         = var.service_underscore,
    "DYNAMODB_TABLE"  = "participant",
    "PARTICIPANTS_TABLE" = "participant",
    "RUNS_CAMPAIGNS_MAPPING_TABLE" = "campaign_run",
    "CAMPAIGNS_TABLE" = "Campaigns"
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
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/participant",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/participant/index/participant-campaign_participant_uniq_handle-created_at-gsi",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/Campaigns",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/campaign_run"
      ]
    }
  }
}

module "list_campaigns_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.7.0"

  create_ecr_repo      = true
  keep_remotely        = true
  keep_locally         = true
  use_image_tag        = false
  image_tag_mutability = "MUTABLE"
  ecr_repo             = local.list_campaigns_function_name_and_ecr_repo_name
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
  source_path = "${local.source_path}/list_campaigns/" # Remember to change
  triggers = {
    dir_sha = local.dir_sha
  }
}

####################################
####################################
####################################
# GET /campaigns/{campaign_id}
####################################
####################################
####################################

module "get_campaign_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.0"

  function_name  = local.get_campaign_function_name_and_ecr_repo_name
  description    = "AWS Educate TPET ${var.service_hyphen} in ${var.environment}: GET /campaigns/{campaign_id}"
  create_package = false
  timeout        = 30

  ##################
  # Container Image
  ##################
  package_type  = "Image"
  architectures = [var.lambda_architecture]
  image_uri     = module.get_campaign_docker_image.image_uri

  publish = true # Whether to publish creation/change as new Lambda Function Version.

  environment_variables = {
    "ENVIRONMENT"     = var.environment,
    "SERVICE"         = var.service_underscore,
    "DYNAMODB_TABLE"  = "participant",
    "PARTICIPANTS_TABLE" = "participant",
    "RUNS_CAMPAIGNS_MAPPING_TABLE" = "campaign_run",
    "CAMPAIGNS_TABLE" = "Campaigns"
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
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/participant",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/participant/index/participant-campaign_participant_uniq_handle-created_at-gsi",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/Campaigns",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/campaign_run"
      ]
    }
  }
}

module "get_campaign_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.7.0"

  create_ecr_repo      = true
  keep_remotely        = true
  keep_locally         = true
  use_image_tag        = false
  image_tag_mutability = "MUTABLE"
  ecr_repo             = local.get_campaign_function_name_and_ecr_repo_name
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
  source_path = "${local.source_path}/get_campaign/" # Remember to change
  triggers = {
    dir_sha = local.dir_sha
  }
}

####################################
####################################
####################################
# POST /campaigns
####################################
####################################
####################################

module "create_campaign_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.0"

  function_name  = local.create_campaign_function_name_and_ecr_repo_name
  description    = "AWS Educate TPET ${var.service_hyphen} in ${var.environment}: POST /campaigns"
  create_package = false
  timeout        = 30

  ##################
  # Container Image
  ##################
  package_type  = "Image"
  architectures = [var.lambda_architecture]
  image_uri     = module.create_campaign_docker_image.image_uri

  publish = true # Whether to publish creation/change as new Lambda Function Version.

  environment_variables = {
    "ENVIRONMENT"     = var.environment,
    "SERVICE"         = var.service_underscore,
    "DYNAMODB_TABLE"  = "participant",
    "PARTICIPANTS_TABLE" = "participant",
    "RUNS_CAMPAIGNS_MAPPING_TABLE" = "campaign_run",
    "CAMPAIGNS_TABLE" = "Campaigns"
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
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/participant",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/participant/index/participant-campaign_participant_uniq_handle-created_at-gsi",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/Campaigns",
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/campaign_run"
      ]
    }
  }
}

module "create_campaign_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.7.0"

  create_ecr_repo      = true
  keep_remotely        = true
  keep_locally         = true
  use_image_tag        = false
  image_tag_mutability = "MUTABLE"
  ecr_repo             = local.create_campaign_function_name_and_ecr_repo_name
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
  source_path = "${local.source_path}/create_campaign/" # Remember to change
  triggers = {
    dir_sha = local.dir_sha
  }
}
