# Create IAM role specifically for refreshing service account tokens
resource "aws_iam_role" "refresh_service_accounts_token_scheduler_role" {
  name = "${var.environment}-${var.service_underscore}-refresh_service_accounts_token-sche-${random_string.this.result}" # 64 characters max

  description = "Role for EventBridge scheduler to trigger refresh service accounts token lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "scheduler.amazonaws.com"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" : data.aws_caller_identity.this.account_id
          }
        }
      }
    ]
  })

  tags = {
    Service = var.service_underscore
  }
}

# Create specific IAM policy for invoking the refresh token lambda
resource "aws_iam_role_policy" "refresh_service_accounts_token_scheduler_policy" {
  name = "${var.environment}-${var.service_underscore}-invoke_refresh_service_accounts_token_lambda-${random_string.this.result}"
  role = aws_iam_role.refresh_service_accounts_token_scheduler_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          module.refresh_service_accounts_token_lambda.lambda_function_arn
        ]
        Condition = {
          StringEquals = {
            "aws:ResourceTag/Environment" : var.environment,
            "aws:ResourceTag/Service" : var.service_underscore
          }
        }
      }
    ]
  })
}
