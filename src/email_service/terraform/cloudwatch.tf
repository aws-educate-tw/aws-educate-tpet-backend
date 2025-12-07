# CloudWatch Alarm for Auto Resumer DLQ
resource "aws_cloudwatch_metric_alarm" "auto_resumer_dlq_has_messages" {
  alarm_name          = "${var.environment}-auto-resumer-dlq-has-messages"
  alarm_description   = "Alarm when the auto-resumer DLQ has messages visible for more than 1 minute"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 60
  statistic           = "Maximum"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  actions_enabled     = true

  dimensions = {
    QueueName = "${var.environment}-auto-resumer-sqs-dlq"
  }

  alarm_actions = [aws_sns_topic.dlq_notifications.arn]
  ok_actions    = [aws_sns_topic.dlq_notifications.arn]
}
