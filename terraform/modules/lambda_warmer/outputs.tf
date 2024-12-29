# Outputs the ARN of the EventBridge Scheduler Group
output "scheduler_group_arn" {
  value       = aws_scheduler_schedule_group.scheduler_group.arn
  description = "ARN of the EventBridge Scheduler Group for Lambda warmer"
}

# Outputs the ARN of the EventBridge Scheduler
output "scheduler_arn" {
  value       = aws_scheduler_schedule.lambda_warmer_schedule.arn
  description = "ARN of the EventBridge Scheduler for Lambda warmer"
}

# Outputs the Lambda function name
output "lambda_function_name" {
  value       = local.lambda_function_name
  description = "Name of the Lambda function for warming other functions"
}

# Outputs the ARN of the Lambda function
output "lambda_function_arn" {
  value       = aws_lambda_function.lambda_warmer.arn
  description = "ARN of the Lambda function for warming other functions"
}

# Outputs the IAM Role name
output "lambda_role_name" {
  value       = aws_iam_role.lambda_role.name
  description = "Name of the IAM Role associated with the Lambda warmer function"
}

# Outputs the ARN of the IAM Role
output "lambda_role_arn" {
  value       = aws_iam_role.lambda_role.arn
  description = "ARN of the IAM Role associated with the Lambda warmer function"
}
