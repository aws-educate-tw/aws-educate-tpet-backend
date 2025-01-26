output "surveycake_access_token_secret_name" {
  value = aws_secretsmanager_secret.surveycake_service_account_access_token.name
}
