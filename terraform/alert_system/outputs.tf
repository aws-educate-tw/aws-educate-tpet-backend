output "dynamodb_table_name" {
  description = "DynamoDB table name for alarm-slack mapping"
  value       = aws_dynamodb_table.alarm_slack_mapping.name
}

output "dynamodb_table_arn" {
  description = "DynamoDB table ARN"
  value       = aws_dynamodb_table.alarm_slack_mapping.arn
}

output "sns_topic_arn" {
  description = "SNS Topic ARN for CloudWatch alarms"
  value       = local.sns_topic_arn
}

output "deployment_summary" {
  description = "Deployment summary with key information"
  value = {
    environment           = var.environment
    region                = var.aws_region
    api_gateway_url       = aws_apigatewayv2_api.slack_interactions.api_endpoint
    slack_interactivity_endpoint = "${aws_apigatewayv2_api.slack_interactions.api_endpoint}/slack/interactivity"
    sns_topic_arn         = local.sns_topic_arn
    dynamodb_table        = aws_dynamodb_table.alarm_slack_mapping.name
  }
}
