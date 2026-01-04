data "aws_sns_topic" "alarm_alert" {
  name = "${var.environment}-cloudwatch-alarm-alert"
}