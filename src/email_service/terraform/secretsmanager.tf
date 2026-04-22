resource "aws_secretsmanager_secret" "jwt_secret" {
  name        = "aws-educate-tpet/${var.environment}/jwt-hs256-secret"
  description = "HS256 secret for generating JWT token for each participant in RSVP type emails"

  tags = {
    Terraform   = "true"
    Environment = var.environment
  }
}

data "aws_secretsmanager_secret_version" "jwt_secret" {
  secret_id = aws_secretsmanager_secret.jwt_secret.id
}
