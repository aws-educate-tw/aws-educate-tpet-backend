resource "aws_cognito_user_pool" "aws_educate_tpet_cognito_user_pool" {
  name                = "${var.environment}-aws_educate_tpet_cognito_user_pool"
  alias_attributes    = ["email"]
  mfa_configuration   = "OPTIONAL"
  deletion_protection = "ACTIVE"
  software_token_mfa_configuration {
    enabled = true
  }

  # Set password policy to not require password change on first login
  password_policy {
    minimum_length                   = 6
    require_lowercase                = false
    require_numbers                  = false
    require_symbols                  = false
    require_uppercase                = false
    temporary_password_validity_days = 180
  }
}

resource "aws_cognito_user_pool_client" "aws_educate_tpet_cognito_client" {
  name                                 = "${var.environment}-aws_educate_tpet_cognito_client"
  allowed_oauth_flows_user_pool_client = true
  generate_secret                      = false
  allowed_oauth_scopes                 = ["aws.cognito.signin.user.admin", "email", "openid", "profile"]
  allowed_oauth_flows                  = ["implicit", "code"]
  explicit_auth_flows                  = ["USER_PASSWORD_AUTH"]
  supported_identity_providers         = ["COGNITO"]

  user_pool_id  = aws_cognito_user_pool.aws_educate_tpet_cognito_user_pool.id
  callback_urls = ["https://tpet.${var.domain_name}"]
  logout_urls   = ["https://tpet.${var.domain_name}"]

  access_token_validity = 24
  id_token_validity     = 24
  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }
}
