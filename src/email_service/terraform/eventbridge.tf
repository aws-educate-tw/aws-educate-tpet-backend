# Create EventBridge scheduler group for scheduled emails
# Schedules in this group are created at runtime by create_email (one per scheduled run), not by Terraform
resource "aws_scheduler_schedule_group" "scheduled_email" {
  name = "${var.environment}-${var.service_underscore}-scheduled-email"
}
