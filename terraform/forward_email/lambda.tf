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
  source_path                                   = "${path.module}/"
  forward_email_function_name_and_ecr_repo_name = "${var.environment}-forward_email-${random_string.this.result}"
  path_include                                  = ["**"]
  path_exclude = [
    "**/__pycache__/**",
    "**/terraform/**",
    "**/.terraform/**",
    "**/*.tfstate",
    "**/*.tfstate.backup",
    "**/.terraform.lock.hcl",
    "**/*.tfvars"
  ]
  files_include = setunion([for f in local.path_include : fileset(local.source_path, f)]...)
  files_exclude = setunion([for f in local.path_exclude : fileset(local.source_path, f)]...)
  files         = sort(setsubtract(local.files_include, local.files_exclude))
  dir_sha       = sha1(join("", [for f in local.files : filesha1("${local.source_path}/${f}")]))
  bucket_name = "${var.environment}-${var.bucket_name}"
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
# Forward Email Lambda #############
####################################
####################################
####################################

module "forward_email_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.0"

  function_name  = local.forward_email_function_name_and_ecr_repo_name
  description    = "AWS Educate TPET forward-email in ${var.environment}: S3 triggered email forwarding"
  create_package = false
  timeout        = 60
  memory_size    = 512

  ##################
  # Container Image
  ##################
  package_type  = "Image"
  architectures = [var.lambda_architecture]
  image_uri     = module.forward_email_docker_image.image_uri

  publish = true # Whether to publish creation/change as new Lambda Function Version.

  environment_variables = {
    "ENVIRONMENT" = var.environment
    "BUCKET_NAME" = local.bucket_name
  }

  allowed_triggers = {
    AllowExecutionFromS3 = {
      service    = "s3"
      source_arn = "arn:aws:s3:::${local.bucket_name}"
    }
  }

  ######################
  # Additional policies
  ######################

  attach_policy_statements = true
  policy_statements = {
    cloudwatch_logs_access = {
      sid    = "CloudwatchLogsAccess"
      effect = "Allow"
      actions = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
      resources = ["*"]
    }
    s3_access = {
      sid    = "S3Access"
      effect = "Allow"
      actions = [
        "s3:GetObject",
        "s3:ListBucket"
      ]
      resources = [
        "arn:aws:s3:::${local.bucket_name}",
        "arn:aws:s3:::${local.bucket_name}/*"
      ]
    }
    ses_access = {
      sid    = "SESAccess"
      effect = "Allow"
      actions = [
        "ses:SendEmail",
        "ses:SendRawEmail"
      ]
      resources = [
        aws_ses_domain_identity.ses_aws_educate_tpet_domain.arn
      ]
    }
  }
}

module "forward_email_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.7.0"

  create_ecr_repo      = true
  keep_remotely        = true
  use_image_tag        = false
  image_tag_mutability = "MUTABLE"
  ecr_repo             = local.forward_email_function_name_and_ecr_repo_name
  ecr_repo_lifecycle_policy = jsonencode({
    "rules" : [
      {
        "rulePriority" : 1,
        "description" : "Keep last 3 images",
        "selection" : {
          "tagStatus" : "any",
          "countType" : "imageCountMoreThan",
          "countNumber" : 3
        },
        "action" : {
          "type" : "expire"
        }
      }
    ]
  })

  source_path      = "${local.source_path}/forward_email/"
  docker_file_path = "Dockerfile"

  triggers = {
    dir_sha = local.dir_sha
  }
}
