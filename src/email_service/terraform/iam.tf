# Create IAM role for EventBridge scheduler to dispatch scheduled runs
resource "aws_iam_role" "dispatch_scheduled_run_scheduler_role" {
  name = "${var.environment}-${var.service_underscore}-dispatch_scheduled_run-scheduler-${random_string.this.result}" # 64 characters max

  description = "Role for EventBridge scheduler to trigger dispatch scheduled run lambda"

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
}

# Create specific IAM policy for invoking the dispatch scheduled run lambda
resource "aws_iam_role_policy" "dispatch_scheduled_run_scheduler_policy" {
  name = "${var.environment}-${var.service_underscore}-invoke_dispatch_scheduled_run_lambda-${random_string.this.result}"
  role = aws_iam_role.dispatch_scheduled_run_scheduler_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          module.dispatch_scheduled_run_lambda.lambda_function_arn
        ]
      }
    ]
  })
}
