resource "aws_secretsmanager_secret" "slack_alert_config" {
  name        = "aws-educate-tpet/${var.environment}/slack/aws-alert/config"
  description = "Slack configuration for alert system"

  tags = {
    Terraform   = "true"
    Environment = var.environment
  }
}
