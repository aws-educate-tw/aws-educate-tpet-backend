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
  source_path_alert   = "${path.module}/slack_alert/"
  source_path_handler = "${path.module}/slack_interaction_handler/"

  slack_alert_function_name_and_ecr_name   = "${var.environment}-slack-alert-${random_string.this.result}"
  slack_handler_function_name_and_ecr_name = "${var.environment}-slack-interaction-handler-${random_string.this.result}"

  path_include = ["**"]
  path_exclude = [
    "**/__pycache__/**",
    "**/terraform/**",
    "**/.terraform/**",
    "**/*.tfstate",
    "**/*.tfstate.backup",
    "**/.terraform.lock.hcl",
    "**/*.tfvars"
  ]

  # Calculate hash for alert
  files_include_alert = setunion([for f in local.path_include : fileset(local.source_path_alert, f)]...)
  files_exclude_alert = setunion([for f in local.path_exclude : fileset(local.source_path_alert, f)]...)
  files_alert         = sort(setsubtract(local.files_include_alert, local.files_exclude_alert))
  dir_sha_alert       = sha1(join("", [for f in local.files_alert : filesha1("${local.source_path_alert}/${f}")]))

  # Calculate hash for handler
  files_include_handler = setunion([for f in local.path_include : fileset(local.source_path_handler, f)]...)
  files_exclude_handler = setunion([for f in local.path_exclude : fileset(local.source_path_handler, f)]...)
  files_handler         = sort(setsubtract(local.files_include_handler, local.files_exclude_handler))
  dir_sha_handler       = sha1(join("", [for f in local.files_handler : filesha1("${local.source_path_handler}/${f}")]))

  # Calculate hash for auto re-enable
  source_path_reenable        = "${path.module}/auto_reenable/"
  files_include_reenable      = setunion([for f in local.path_include : fileset(local.source_path_reenable, f)]...)
  files_exclude_reenable      = setunion([for f in local.path_exclude : fileset(local.source_path_reenable, f)]...)
  files_reenable              = sort(setsubtract(local.files_include_reenable, local.files_exclude_reenable))
  dir_sha_reenable            = sha1(join("", [for f in local.files_reenable : filesha1("${local.source_path_reenable}/${f}")]))
  auto_reenable_function_name = "${var.environment}-auto-reenable-${random_string.this.result}"

}

provider "docker" {
  registry_auth {
    address  = format("%v.dkr.ecr.%v.amazonaws.com", data.aws_caller_identity.this.account_id, var.aws_region)
    username = data.aws_ecr_authorization_token.token.user_name
    password = data.aws_ecr_authorization_token.token.password
  }
}

#################################################
#################################################
#################################################
# Pipeline 1: Slack Alert Lambda #############
#################################################
#################################################
#################################################

module "slack_alert_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.0"

  function_name  = local.slack_alert_function_name_and_ecr_name
  description    = "Slack Alert - Renders CloudWatch alarms to Slack with incident lifecycle"
  create_package = false
  timeout        = 60
  memory_size    = 512

  package_type  = "Image"
  architectures = [var.lambda_architecture]
  image_uri     = module.slack_alert_docker_image.image_uri

  publish = true

  environment_variables = {
    ENVIRONMENT                   = var.environment
    INCIDENT_TABLE                = aws_dynamodb_table.alarm_slack_mapping.name
    SLACK_ALERT_CONFIG_SECRET_ARN = aws_secretsmanager_secret.slack_alert_config.arn
  }

  allowed_triggers = {
    SNS = {
      principal  = "sns.amazonaws.com"
      source_arn = local.sns_topic_arn
    }
  }

  attach_policy_statements = true
  policy_statements = {
    dynamodb = {
      sid    = "AllowDynamoDBAccess"
      effect = "Allow"
      actions = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem"
      ]
      resources = [aws_dynamodb_table.alarm_slack_mapping.arn]
    }
    sns = {
      sid    = "AllowSNSPublish"
      effect = "Allow"
      actions = [
        "sns:Publish"
      ]
      resources = [local.sns_topic_arn]
    }
    cloudwatch = {
      sid    = "AllowCloudWatchMetricWidget"
      effect = "Allow"
      actions = [
        "cloudwatch:GetMetricWidgetImage"
      ]
      resources = ["*"]
    }
    secrets_manager = {
      sid       = "AllowSecretsManagerRead"
      effect    = "Allow"
      actions   = ["secretsmanager:GetSecretValue"]
      resources = [aws_secretsmanager_secret.slack_alert_config.arn]
    }
  }

  tags = {
    Terraform   = "true"
    Environment = var.environment
  }
}

module "slack_alert_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.7.0"

  create_ecr_repo      = true
  keep_remotely        = true
  use_image_tag        = false
  image_tag_mutability = "MUTABLE"
  ecr_repo             = local.slack_alert_function_name_and_ecr_name

  ecr_repo_lifecycle_policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 3 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 3
        }
        action = {
          type = "expire"
        }
      }
    ]
  })

  source_path      = path.module
  docker_file_path = "slack_alert/Dockerfile"

  triggers = {
    dir_sha = local.dir_sha_alert
  }
}

resource "aws_sns_topic_subscription" "trigger_alert" {
  topic_arn = local.sns_topic_arn
  protocol  = "lambda"
  endpoint  = module.slack_alert_lambda.lambda_function_arn
}

#################################################
#################################################
#################################################
# Pipeline 2: Slack Interaction Handler Lambda
#################################################
#################################################
#################################################

module "slack_interaction_handler_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.0"

  function_name  = local.slack_handler_function_name_and_ecr_name
  description    = "Slack Interaction Handler - Processes button clicks from Slack"
  create_package = false
  timeout        = 30
  memory_size    = 256

  package_type  = "Image"
  architectures = [var.lambda_architecture]
  image_uri     = module.slack_interaction_handler_docker_image.image_uri

  publish = true

  environment_variables = {
    ENVIRONMENT                   = var.environment
    INCIDENT_TABLE                = aws_dynamodb_table.alarm_slack_mapping.name
    SLACK_ALERT_CONFIG_SECRET_ARN = aws_secretsmanager_secret.slack_alert_config.arn
  }

  attach_policy_statements = true
  policy_statements = {
    dynamodb = {
      sid    = "AllowDynamoDBAccess"
      effect = "Allow"
      actions = [
        "dynamodb:GetItem",
        "dynamodb:UpdateItem"
      ]
      resources = [aws_dynamodb_table.alarm_slack_mapping.arn]
    }
    cloudwatch = {
      sid    = "AllowCloudWatchAlarmActions"
      effect = "Allow"
      actions = [
        "cloudwatch:SetAlarmState",
        "cloudwatch:DisableAlarmActions",
        "cloudwatch:EnableAlarmActions",
        "cloudwatch:DescribeAlarms"
      ]
      resources = ["*"]
    }
    secrets_manager = {
      sid       = "AllowSecretsManagerRead"
      effect    = "Allow"
      actions   = ["secretsmanager:GetSecretValue"]
      resources = [aws_secretsmanager_secret.slack_alert_config.arn]
    }
  }

  tags = {
    Terraform   = "true"
    Environment = var.environment
  }
}

module "slack_interaction_handler_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.7.0"

  create_ecr_repo      = true
  keep_remotely        = true
  use_image_tag        = false
  image_tag_mutability = "MUTABLE"
  ecr_repo             = local.slack_handler_function_name_and_ecr_name

  ecr_repo_lifecycle_policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 3 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 3
        }
        action = {
          type = "expire"
        }
      }
    ]
  })

  source_path      = path.module
  docker_file_path = "slack_interaction_handler/Dockerfile"

  triggers = {
    dir_sha = local.dir_sha_handler
  }
}

#################################################
#################################################
#################################################
# Pipeline 3: Auto Re-enable Lambda
#################################################
#################################################
#################################################

module "auto_reenable_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.0"

  function_name  = local.auto_reenable_function_name
  description    = "Auto re-enable alarm actions when alarm state becomes OK"
  create_package = false
  timeout        = 30
  memory_size    = 256

  package_type  = "Image"
  architectures = [var.lambda_architecture]
  image_uri     = module.auto_reenable_docker_image.image_uri

  publish = true

  environment_variables = {
    ENVIRONMENT                   = var.environment
    INCIDENT_TABLE                = aws_dynamodb_table.alarm_slack_mapping.name
    SLACK_ALERT_CONFIG_SECRET_ARN = aws_secretsmanager_secret.slack_alert_config.arn
  }

  attach_policy_statements = true
  policy_statements = {
    cloudwatch = {
      sid    = "AllowEnableAlarmActions"
      effect = "Allow"
      actions = [
        "cloudwatch:EnableAlarmActions"
      ]
      resources = ["*"]
    }
    dynamodb = {
      sid    = "AllowDynamoDBAccess"
      effect = "Allow"
      actions = [
        "dynamodb:GetItem",
        "dynamodb:UpdateItem"
      ]
      resources = [aws_dynamodb_table.alarm_slack_mapping.arn]
    }
    secrets_manager = {
      sid       = "AllowSecretsManagerRead"
      effect    = "Allow"
      actions   = ["secretsmanager:GetSecretValue"]
      resources = [aws_secretsmanager_secret.slack_alert_config.arn]
    }
  }

  tags = {
    Terraform   = "true"
    Environment = var.environment
  }
}

module "auto_reenable_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.7.0"

  create_ecr_repo      = true
  keep_remotely        = true
  use_image_tag        = false
  image_tag_mutability = "MUTABLE"
  ecr_repo             = local.auto_reenable_function_name

  ecr_repo_lifecycle_policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 3 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 3
        }
        action = {
          type = "expire"
        }
      }
    ]
  })

  source_path      = path.module
  docker_file_path = "auto_reenable/Dockerfile"

  triggers = {
    dir_sha = local.dir_sha_reenable
  }
}
