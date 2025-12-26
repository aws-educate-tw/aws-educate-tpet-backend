resource "aws_api_gateway_rest_api" "onboarding_api" {
  name = "onboarding-ariel-api"
}

resource "aws_api_gateway_resource" "onboarding_ariel" {
  rest_api_id = aws_api_gateway_rest_api.onboarding_api.id
  parent_id   = aws_api_gateway_rest_api.onboarding_api.root_resource_id
  path_part   = "onboarding_ariel" # 網址路徑改為 /onboarding_ariel
}

resource "aws_api_gateway_method" "onboarding_ariel" {
  rest_api_id   = aws_api_gateway_rest_api.onboarding_api.id
  resource_id   = aws_api_gateway_resource.onboarding_ariel.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "onboarding_ariel" {
  rest_api_id = aws_api_gateway_rest_api.onboarding_api.id
  resource_id = aws_api_gateway_resource.onboarding_ariel.id
  http_method = aws_api_gateway_method.onboarding_ariel.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = module.onboarding_lambda.lambda_function_invoke_arn
}

resource "aws_api_gateway_deployment" "this" {
  rest_api_id = aws_api_gateway_rest_api.onboarding_api.id

  triggers = {
    redeploy = sha1(jsonencode(aws_api_gateway_resource.onboarding_ariel))
  }

  depends_on = [
    aws_api_gateway_integration.onboarding_ariel
  ]
}

resource "aws_api_gateway_stage" "dev" {
  rest_api_id   = aws_api_gateway_rest_api.onboarding_api.id
  deployment_id = aws_api_gateway_deployment.this.id
  stage_name    = var.environment
}

# trigger report