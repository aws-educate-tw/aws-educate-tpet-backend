resource "aws_apigatewayv2_api" "onboarding" {
  name          = "onboarding-api-aaron"
  protocol_type = "HTTP"

  cors_configuration {
    allow_headers     = ["content-type", "x-amz-date", "authorization", "x-api-key", "x-amz-security-token", "x-amz-user-agent"]
    allow_methods     = ["*"]
    allow_origins     = ["http://localhost:3000", "http://localhost:5500", "https://*"]
    allow_credentials = true
  }

}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id           = aws_apigatewayv2_api.onboarding.id
  integration_type = "AWS_PROXY"
  integration_uri  = module.onboarding_lambda.lambda_function_arn
}

resource "aws_apigatewayv2_route" "get_onboarding" {
  api_id    = aws_apigatewayv2_api.onboarding.id
  route_key = "GET /onboarding/aaron"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.onboarding.id
  name        = var.environment
  auto_deploy = true
}
