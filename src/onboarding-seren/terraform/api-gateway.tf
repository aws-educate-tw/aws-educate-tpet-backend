resource "aws_apigatewayv2_api" "onboarding" {
  name          = "onboarding-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id           = aws_apigatewayv2_api.onboarding.id
  integration_type = "AWS_PROXY"
  integration_uri  = module.onboarding_lambda.lambda_function_arn
}

resource "aws_apigatewayv2_route" "get_onboarding" {
  api_id    = aws_apigatewayv2_api.onboarding.id
  route_key = "GET /onboarding/seren"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "stage" {
  api_id      = aws_apigatewayv2_api.onboarding.id
  name        = var.environment
  auto_deploy = true
}