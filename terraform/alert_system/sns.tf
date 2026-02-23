# SNS Topic for CloudWatch Alarms
# This can either reference an existing topic or create a new one

locals {
  sns_topic_arn = try(aws_sns_topic.alarm_alert[0].arn, null)
}

resource "aws_sns_topic" "alarm_alert" {
  count        = var.create_sns_topic ? 1 : 0
  name         = "${var.environment}-cloudwatch-alarm-alert"
  display_name = "CloudWatch Alarm alert"

  tags = {
    Environment = var.environment
    Terraform   = "true"
  }
}
