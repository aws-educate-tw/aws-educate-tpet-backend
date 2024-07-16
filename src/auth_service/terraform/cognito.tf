resource "aws_cognito_user_pool" "aws_educate_tpet_cognito_user_pool" {
  name = "aws_educate_tpet_cognito_user_pool"
}

resource "aws_cognito_user_pool_client" "aws_educate_tpet_cognito_client" {
  name                                 = "aws_educate_tpet_cognito_client"
  allowed_oauth_flows_user_pool_client = true
  generate_secret                      = false
  allowed_oauth_scopes                 = ["aws.cognito.signin.user.admin", "email", "openid", "profile"]
  allowed_oauth_flows                  = ["implicit", "code"]
  explicit_auth_flows                  = ["ADMIN_NO_SRP_AUTH", "USER_PASSWORD_AUTH"]
  supported_identity_providers         = ["COGNITO"]

  user_pool_id  = aws_cognito_user_pool.aws_educate_tpet_cognito_user_pool.id
  callback_urls = ["https://tpet.aws-educate.tw"]
  logout_urls   = ["https://tpet.aws-educate.tw"]
}
