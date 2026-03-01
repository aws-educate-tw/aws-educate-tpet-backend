data "aws_secretsmanager_secret" "slack_alert_channel_id" {
  name = "aws-educate-tpet/${var.environment}/slack/aws-alert/channel-id"
}

data "aws_secretsmanager_secret" "slack_workspace_id" {
  name = "aws-educate-tpet/${var.environment}/slack/slack-workspace-id"
}

data "aws_secretsmanager_secret" "slack_alert_bot_app_id" {
  name = "aws-educate-tpet/${var.environment}/slack/aws-alert/alert-bot/slack-app-id"
}

data "aws_secretsmanager_secret" "slack_alert_bot_client_id" {
  name = "aws-educate-tpet/${var.environment}/slack/aws-alert/alert-bot/slack-client-id"
}

data "aws_secretsmanager_secret" "slack_alert_bot_secret" {
  name = "aws-educate-tpet/${var.environment}/slack/aws-alert/alert-bot/slack-bot-secret"
}

data "aws_secretsmanager_secret" "slack_alert_bot_verification_token" {
  name = "aws-educate-tpet/${var.environment}/slack/aws-alert/alert-bot/verification-token"
}

data "aws_secretsmanager_secret" "slack_alert_bot_signing_secret" {
  name = "aws-educate-tpet/${var.environment}/slack/aws-alert/alert-bot/signing_secret"
}
data "aws_secretsmanager_secret_version" "slack_alert_channel_id" {
  secret_id = data.aws_secretsmanager_secret.slack_alert_channel_id.id
}

data "aws_secretsmanager_secret_version" "slack_workspace_id" {
  secret_id = data.aws_secretsmanager_secret.slack_workspace_id.id
}

data "aws_secretsmanager_secret_version" "slack_alert_bot_app_id" {
  secret_id = data.aws_secretsmanager_secret.slack_alert_bot_app_id.id
}

data "aws_secretsmanager_secret_version" "slack_alert_bot_client_id" {
  secret_id = data.aws_secretsmanager_secret.slack_alert_bot_client_id.id
}

data "aws_secretsmanager_secret_version" "slack_alert_bot_secret" {
  secret_id = data.aws_secretsmanager_secret.slack_alert_bot_secret.id
}

data "aws_secretsmanager_secret_version" "slack_alert_bot_verification_token" {
  secret_id = data.aws_secretsmanager_secret.slack_alert_bot_verification_token.id
}

data "aws_secretsmanager_secret_version" "slack_alert_bot_signing_secret" {
  secret_id = data.aws_secretsmanager_secret.slack_alert_bot_signing_secret.id
}
