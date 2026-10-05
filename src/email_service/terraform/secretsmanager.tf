data "aws_secretsmanager_secret" "jwt_secret" {
  name = "aws-educate-tpet/${var.environment}/jwt-hs256-secret"
}

data "aws_secretsmanager_secret_version" "jwt_secret" {
  secret_id = data.aws_secretsmanager_secret.jwt_secret.id
}
