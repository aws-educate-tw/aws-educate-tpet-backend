# Create EventBridge scheduler group
resource "aws_scheduler_schedule_group" "service_group" {
  name = "${var.environment}-${var.service_underscore}-schedule_group"

  tags = {
    Service = var.service_underscore
  }
}

# Create EventBridge scheduler
resource "aws_scheduler_schedule" "refresh_service_accounts_token" {
  name        = "${var.environment}-${var.service_underscore}-refresh_service_accounts_token"
  group_name  = aws_scheduler_schedule_group.service_group.name
  description = "Schedule to refresh service accounts token every 23 hours"

  flexible_time_window {
    mode = "OFF" # Run exactly at scheduled time
  }

  schedule_expression = "rate(23 hours)"

  target {
    arn      = module.refresh_service_accounts_token_lambda.lambda_function_arn
    role_arn = aws_iam_role.refresh_service_accounts_token_scheduler_role.arn
    retry_policy {
      maximum_retry_attempts = 0 # Explicitly disable retries
    }
  }
}


# Outputs
output "scheduler_group_arn" {
  value       = aws_scheduler_schedule_group.service_group.arn
  description = "ARN of the EventBridge scheduler group"
}

output "scheduler_arn" {
  value       = aws_scheduler_schedule.refresh_service_accounts_token.arn
  description = "ARN of the EventBridge scheduler for token refresh"
}
