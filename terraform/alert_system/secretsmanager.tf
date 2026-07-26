resource "aws_secretsmanager_secret" "slack_alert_config" {
  name        = "aws-educate-tpet/${var.environment}/slack/aws-alert/config"
  description = "Slack configuration for alert system"

  tags = {
    Terraform   = "true"
    Environment = var.environment
  }
}

data "aws_secretsmanager_secret_version" "slack_alert_config" {
  secret_id = aws_secretsmanager_secret.slack_alert_config.id
}

locals {
  slack_alert_config = jsondecode(data.aws_secretsmanager_secret_version.slack_alert_config.secret_string)
}
