data "aws_region" "current" {}

locals {
  email_service_dlq_message_count_gte_1_alarm_name = "[P2][Email-Service] - DLQ Message Count >= 1"
  auto_resumer_log_group_name                      = "/aws/lambda/${local.auto_resume_aurora_function_name_and_ecr_repo_name}"
}

#########################################################
#########################################################
#########################################################
# Auto-resumer DLQ Message Count >= 1 ###################
#########################################################
#########################################################
#########################################################
resource "aws_cloudwatch_metric_alarm" "email_service_dlq_message_count_gte_1" {
  # Title: [Severity][Service] - {condition}
  alarm_name = local.email_service_dlq_message_count_gte_1_alarm_name

  # Description format: Simplified to single line per field
  alarm_description = <<EOT
Level: P2
Condition: ApproximateNumberOfMessagesVisible >= 1 and over 1 minute
Runbook: https://www.notion.so/aws-educate-tw/SRE-Email-Service-Auto-resumer-DLQ-Message-Count-0-2db6bfee6817802aac4ee7bd0783c3bf
Observability Links: CloudWatch Alarm: https://console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#alarmsV2:alarm/${replace(urlencode(local.email_service_dlq_message_count_gte_1_alarm_name), "+", "%20")} | Logs: https://console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#logsV2:log-groups/log-group/${urlencode(local.auto_resumer_log_group_name)}
PIC: Kiki Huang
EOT

  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 60
  statistic           = "Maximum"
  threshold           = 0

  dimensions = {
    QueueName = module.auto_resumer_sqs.dead_letter_queue_name
  }

  alarm_actions = [data.aws_sns_topic.alarm_alert.arn]
  ok_actions    = [data.aws_sns_topic.alarm_alert.arn]

  tags = {
    Service     = "email-service"
    Environment = var.environment
    Owner       = "TPET"
    Severity    = "P2"
  }
}
