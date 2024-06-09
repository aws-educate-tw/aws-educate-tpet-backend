resource "aws_api_gateway_rest_api" "files_api" {
  name        = "Files API"
  description = "API for listing files with pagination and filtering"
}

resource "aws_api_gateway_resource" "files_resource" {
  rest_api_id = aws_api_gateway_rest_api.files_api.id
  parent_id   = aws_api_gateway_rest_api.files_api.root_resource_id
  path_part   = "files"
}

# GET Method
resource "aws_api_gateway_method" "list_files_method" {
  rest_api_id   = aws_api_gateway_rest_api.files_api.id
  resource_id   = aws_api_gateway_resource.files_resource.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "list_files_integration" {
  rest_api_id             = aws_api_gateway_rest_api.files_api.id
  resource_id             = aws_api_gateway_resource.files_resource.id
  http_method             = aws_api_gateway_method.list_files_method.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = aws_lambda_function.list_files.invoke_arn
}

resource "aws_api_gateway_method_response" "list_files_response_200" {
  rest_api_id = aws_api_gateway_rest_api.files_api.id
  resource_id = aws_api_gateway_resource.files_resource.id
  http_method = aws_api_gateway_method.list_files_method.http_method
  status_code = "200"

  # CORS Settings
  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = true,
    "method.response.header.Access-Control-Allow-Headers" = true,
    "method.response.header.Access-Control-Allow-Methods" = true
  }
}

resource "aws_api_gateway_integration_response" "list_files_integration_response_200" {
  rest_api_id = aws_api_gateway_rest_api.files_api.id
  resource_id = aws_api_gateway_resource.files_resource.id
  http_method = aws_api_gateway_method.list_files_method.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = "'${var.cors_allow_origin}'",
    "method.response.header.Access-Control-Allow-Headers" = "'*'",
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS,POST,PUT'"
  }
}

# OPTIONS Method
resource "aws_api_gateway_method" "options_method" {
  rest_api_id   = aws_api_gateway_rest_api.files_api.id
  resource_id   = aws_api_gateway_resource.files_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_integration" {
  rest_api_id = aws_api_gateway_rest_api.files_api.id
  resource_id = aws_api_gateway_resource.files_resource.id
  http_method = aws_api_gateway_method.options_method.http_method
  type        = "MOCK"
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_response_200" {
  rest_api_id = aws_api_gateway_rest_api.files_api.id
  resource_id = aws_api_gateway_resource.files_resource.id
  http_method = aws_api_gateway_method.options_method.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true,
    "method.response.header.Access-Control-Allow-Methods" = true,
    "method.response.header.Access-Control-Allow-Origin"  = true
  }

  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration_response" "options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.files_api.id
  resource_id = aws_api_gateway_resource.files_resource.id
  http_method = aws_api_gateway_method.options_method.http_method
  status_code = aws_api_gateway_method_response.options_response_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS,POST,PUT'",
    "method.response.header.Access-Control-Allow-Origin"  = "'${var.cors_allow_origin}'"
  }
}

resource "aws_api_gateway_deployment" "files_api_deployment" {
  depends_on = [
    aws_api_gateway_integration.list_files_integration,
    aws_api_gateway_method_response.list_files_response_200,
    aws_api_gateway_integration_response.list_files_integration_response_200,
    aws_api_gateway_method.options_method,
    aws_api_gateway_method_response.options_response_200,
    aws_api_gateway_integration.options_integration,
    aws_api_gateway_integration_response.options_integration_response
  ]
  rest_api_id = aws_api_gateway_rest_api.files_api.id
  stage_name  = var.environment

  triggers = {
    redeployment = timestamp()
  }
}


