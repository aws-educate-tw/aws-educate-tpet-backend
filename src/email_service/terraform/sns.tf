# SNS Topic for DLQ notifications
resource "aws_sns_topic" "dlq_notifications" {
  name         = "${var.environment}-email-service-dlq-notifications"
  display_name = "Email Service DLQ Notifications"
}
