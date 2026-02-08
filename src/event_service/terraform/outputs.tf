output "eventbridge_scheduler_role_arn" {
  description = "IAM role ARN assumed by EventBridge Scheduler to invoke SyncAuroraLambda"
  value       = aws_iam_role.eventbridge_scheduler_role.arn
}
