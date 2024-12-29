provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      "Terraform"   = "true",
      "Environment" = var.environment,
    }
  }
}

# Generate a random string for unique Lambda function and IAM Role names
resource "random_string" "suffix" {
  length  = 4
  special = false
  lower   = true
  upper   = false
}

# Construct the Lambda function name
locals {
  lambda_function_name = "${var.environment}-${var.aws_region}-lambda_warmer-${random_string.suffix.result}"
}

# Archive the internal Python code for Lambda
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_warmer/"
  output_path = "${path.module}/lambda_warmer.zip"
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "${local.lambda_function_name}-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# IAM Policy for Lambda
resource "aws_iam_policy" "lambda_policy" {
  name = "${local.lambda_function_name}-lambda-policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "lambda:ListFunctions",
          "lambda:ListTags",
          "lambda:InvokeFunction"
        ],
        Effect   = "Allow",
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# IAM Role for EventBridge Scheduler
resource "aws_iam_role" "scheduler_role" {
  name = "${local.lambda_function_name}-scheduler-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "scheduler.amazonaws.com"
      }
    }]
  })
}

# IAM Policy for EventBridge Scheduler
resource "aws_iam_policy" "scheduler_policy" {
  name = "${local.lambda_function_name}-scheduler-policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "lambda:InvokeFunction"
        ],
        Effect   = "Allow",
        Resource = aws_lambda_function.lambda_warmer.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "scheduler_policy_attachment" {
  role       = aws_iam_role.scheduler_role.name
  policy_arn = aws_iam_policy.scheduler_policy.arn
}

# Lambda Function
resource "aws_lambda_function" "lambda_warmer" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = local.lambda_function_name
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.11"
  source_code_hash = filebase64sha256(data.archive_file.lambda_zip.output_path)
  description      = "Lambda function to warm other functions"
  timeout          = 60

  environment {
    variables = {
      PREWARM_TAG_KEY   = var.prewarm_tag_key
      PREWARM_TAG_VALUE = var.prewarm_tag_value
    }
  }
}

# EventBridge Scheduler Group
resource "aws_scheduler_schedule_group" "scheduler_group" {
  name = "${local.lambda_function_name}-scheduler-group"
}

# EventBridge Scheduler
resource "aws_scheduler_schedule" "lambda_warmer_schedule" {
  name        = "${local.lambda_function_name}-schedule"
  group_name  = aws_scheduler_schedule_group.scheduler_group.name
  description = "Schedule to invoke warmer Lambda function"

  flexible_time_window {
    mode = "OFF" # Run exactly at scheduled time
  }

  schedule_expression = var.lambda_schedule_expression

  target {
    arn      = aws_lambda_function.lambda_warmer.arn
    role_arn = aws_iam_role.scheduler_role.arn

    retry_policy {
      maximum_retry_attempts = var.scheduler_max_retry_attempts
    }
  }
}
