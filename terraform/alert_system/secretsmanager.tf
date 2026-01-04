data "aws_secretsmanager_secret" "slack_bot" {
  name = "${var.environment}/alerts/slack/bot"
}

data "aws_secretsmanager_secret_version" "slack_bot" {
  secret_id = data.aws_secretsmanager_secret.slack_bot.id
}