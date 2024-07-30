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
  source_path                                    = "${path.module}/.."
  validate_input_function_name_and_ecr_repo_name = "${var.environment}-${var.service_underscore}-validate_input-${random_string.this.result}"
  send_email_function_name_and_ecr_repo_name     = "${var.environment}-${var.service_underscore}-send_email-${random_string.this.result}"
  path_include                                   = ["**"]
  path_exclude                                   = ["**/__pycache__/**"]
  files_include                                  = setunion([for f in local.path_include : fileset(local.source_path, f)]...)
  files_exclude                                  = setunion([for f in local.path_exclude : fileset(local.source_path, f)]...)
  files                                          = sort(setsubtract(local.files_include, local.files_exclude))
  dir_sha                                        = sha1(join("", [for f in local.files : filesha1("${local.source_path}/${f}")]))
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
# POST /send-email #################
####################################
####################################
####################################

module "validate_input_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.0"

  function_name  = local.validate_input_function_name_and_ecr_repo_name                             # Remember to change
  description    = "AWS Educate TPET ${var.service_hyphen} in ${var.environment}: POST /send-email" # Remember to change
  create_package = false
  timeout        = 60
  memory_size    = 512

  ##################
  # Container Image
  ##################
  package_type  = "Image"
  architectures = ["x86_64"]                                   # or ["arm64"]
  image_uri     = module.validate_input_docker_image.image_uri # Remember to change

  publish = true # Whether to publish creation/change as new Lambda Function Version.


  environment_variables = {
    "ENVIRONMENT"   = var.environment,
    "SERVICE"       = var.service_underscore
    "BUCKET_NAME"   = "${var.environment}-aws-educate-tpet-storage"
    "SQS_QUEUE_URL" = module.send_email_sqs.queue_url
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
    },
    sqs_send_message = {
      effect = "Allow",
      actions = [
        "sqs:SendMessage"
      ],
      resources = [
        "arn:aws:sqs:${var.aws_region}:${data.aws_caller_identity.this.account_id}:${module.send_email_sqs.queue_name}"
      ]
    }
  }
}

module "validate_input_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.7.0"

  create_ecr_repo      = true
  keep_remotely        = true
  use_image_tag        = false
  image_tag_mutability = "MUTABLE"
  ecr_repo             = local.validate_input_function_name_and_ecr_repo_name # Remember to change
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
  source_path = "${local.source_path}/validate_input/" # Remember to change
  triggers = {
    dir_sha = local.dir_sha
  }

}

module "send_email_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.0"

  function_name = local.send_email_function_name_and_ecr_repo_name
  description   = "AWS Educate TPET ${var.service_hyphen} in ${var.environment}: POST /send-email"
  event_source_mapping = {
    sqs = {
      event_source_arn        = module.send_email_sqs.queue_arn
      function_response_types = ["ReportBatchItemFailures"] # Setting to ["ReportBatchItemFailures"] means that when the Lambda function processes a batch of SQS messages, it can report which messages failed to process.
      scaling_config = {
        # The `maximum_concurrency` parameter limits the number of concurrent Lambda instances that can process messages from the SQS queue.
        # Setting `maximum_concurrency = 5` means that up to 5 Lambda instances can run simultaneously, each processing different messages from the SQS queue.
        # It ensures that multiple messages can be processed in parallel, increasing throughput, but each message is still processed only once by a single Lambda instance.
        maximum_concurrency = 20
      }
    }
  }
  create_package = false
  timeout        = 600
  memory_size    = 1024

  ##################
  # Container Image
  ##################
  package_type  = "Image"
  architectures = ["x86_64"] # or ["arm64"]
  image_uri     = module.docker_image.image_uri

  publish = true # Whether to publish creation/change as new Lambda Function Version.


  environment_variables = {
    "ENVIRONMENT"         = var.environment,
    "SERVICE"             = var.service_underscore
    "DYNAMODB_TABLE"      = var.dynamodb_table
    "BUCKET_NAME"         = "${var.environment}-aws-educate-tpet-storage"
    "PRIVATE_BUCKET_NAME" = "${var.environment}-aws-educate-tpet-private-storage"
    "SQS_QUEUE_URL"       = module.send_email_sqs.queue_url
  }

  allowed_triggers = {
    allow_execution_from_sqs = {
      principal  = "sqs.amazonaws.com"
      source_arn = module.send_email_sqs.queue_arn
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
        "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.this.account_id}:table/${var.dynamodb_table}/index/*"
      ]
    },
    ses_send_email = {
      effect = "Allow",
      actions = [
        "ses:SendEmail",
        "ses:SendRawEmail"
      ],
      resources = [
        "arn:aws:ses:ap-northeast-1:${data.aws_caller_identity.this.account_id}:identity/awseducate.cloudambassador@gmail.com",
        "arn:aws:ses:ap-northeast-1:${data.aws_caller_identity.this.account_id}:identity/aws-educate.tw"
      ]
    },
    sqs_receive_message = {
      effect = "Allow",
      actions = [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes"
      ],
      resources = [
        "arn:aws:sqs:${var.aws_region}:${data.aws_caller_identity.this.account_id}:${module.send_email_sqs.queue_name}"
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
        "arn:aws:s3:::${var.environment}-aws-educate-tpet-storage/*",
        "arn:aws:s3:::${var.environment}-aws-educate-tpet-private-storage",
        "arn:aws:s3:::${var.environment}-aws-educate-tpet-private-storage/*"
      ]
    }
  }
}

module "docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.7.0"

  create_ecr_repo      = true
  keep_remotely        = true
  use_image_tag        = false
  image_tag_mutability = "MUTABLE"
  ecr_repo             = local.send_email_function_name_and_ecr_repo_name
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
  source_path = "${local.source_path}/send_email/" # Remember to change
  triggers = {
    dir_sha = local.dir_sha
  }

}
