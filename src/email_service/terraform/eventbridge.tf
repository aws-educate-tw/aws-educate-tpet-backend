locals {
  scheduler_role_name = "${var.environment}-${var.service_hyphen}-scheduler"
}

resource "aws_iam_role" "eventbridge_scheduler_role" {
  name = local.scheduler_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "scheduler.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "eventbridge_scheduler_invoke_lambda" {
  name = "${local.scheduler_role_name}-invoke-lambda"
  role = aws_iam_role.eventbridge_scheduler_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "lambda:InvokeFunction"
        ],
        Resource = [
          module.sync_aurora_lambda.lambda_function_arn
        ]
      }
    ]
  })
}
