resource "aws_apigatewayv2_api" "slack_interactions" {
  name          = "${var.environment}-slack-interactions"
  protocol_type = "HTTP"
  description   = "API Gateway for Slack button interactions"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST", "OPTIONS"]
    allow_headers = ["*"]
  }

  tags = {
    Environment = var.environment
    Terraform   = "true"
  }
}

resource "aws_apigatewayv2_stage" "slack_interactions_api_gw_stage" {
  api_id      = aws_apigatewayv2_api.slack_interactions.id
  name        = "${var.environment}"
  auto_deploy = true

  tags = {
    Environment = var.environment
    Terraform   = "true"
  }
}

resource "aws_apigatewayv2_integration" "slack_interaction_handler" {
  api_id                 = aws_apigatewayv2_api.slack_interactions.id
  integration_type       = "AWS_PROXY"
  integration_uri        = module.slack_interaction_handler_lambda.lambda_function_invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "slack_interactivity" {
  api_id    = aws_apigatewayv2_api.slack_interactions.id
  route_key = "POST /slack/interactivity"
  target    = "integrations/${aws_apigatewayv2_integration.slack_interaction_handler.id}"
}

resource "aws_lambda_permission" "api_gateway_invoke" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = module.slack_interaction_handler_lambda.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.slack_interactions.execution_arn}/*/*"
}

output "api_gateway_url" {
  description = "API Gateway endpoint URL for Slack interactions"
  value       = aws_apigatewayv2_api.slack_interactions.api_endpoint
}

output "slack_interaction_endpoint" {
  description = "Full Slack interaction endpoint URL"
  value       = "${aws_apigatewayv2_api.slack_interactions.api_endpoint}/${aws_apigatewayv2_stage.slack_interactions_api_gw_stage.name}/slack/interactivity"
}
