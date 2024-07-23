resource "aws_ssm_parameter" "aws_educate_tpet_cognito_user_pool_id" {
  name  = "${var.environment}-aws_educate_tpet_cognito_user_pool_id"
  type  = "String"
  value = aws_cognito_user_pool.aws_educate_tpet_cognito_user_pool.id
}

resource "aws_ssm_parameter" "aws_educate_tpet_cognito_client_id" {
  name  = "${var.environment}-aws_educate_tpet_cognito_client_id"
  type  = "String"
  value = aws_cognito_user_pool_client.aws_educate_tpet_cognito_client.id
}
