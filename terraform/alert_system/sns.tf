# SNS Topic for CloudWatch Alarms

locals {
  sns_topic_arn = aws_sns_topic.alarm_alert.arn
}

resource "aws_sns_topic" "alarm_alert" {
  name         = "${var.environment}-slack-notification"
  display_name = "Slack Notification"

  tags = {
    Environment = var.environment
    Terraform   = "true"
  }
}
