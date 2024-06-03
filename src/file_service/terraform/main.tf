provider "aws" {
  region = "ap-northeast-1"
}

data "aws_region" "current" {}


resource "aws_iam_role" "lambda_exec_role" {
  name = "lambda_exec_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  managed_policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    "arn:aws:iam::aws:policy/AmazonDynamoDBReadOnlyAccess"
  ]
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../list_files"
  output_path = "${path.module}/list_file_function.zip"
}

resource "aws_lambda_function" "list_files" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "list_files"
  role             = aws_iam_role.lambda_exec_role.arn
  handler          = "list_file_function.lambda_handler"
  source_code_hash = filebase64sha256(data.archive_file.lambda_zip.output_path)
  runtime          = "python3.11"

  environment {
    variables = {
      TABLE_NAME = "file"
    }
  }
}

resource "aws_api_gateway_rest_api" "files_api" {
  name        = "Files API"
  description = "API for listing files with pagination and filtering"
}

resource "aws_api_gateway_resource" "files_resource" {
  rest_api_id = aws_api_gateway_rest_api.files_api.id
  parent_id   = aws_api_gateway_rest_api.files_api.root_resource_id
  path_part   = "files"
}

resource "aws_api_gateway_method" "get_files_method" {
  rest_api_id   = aws_api_gateway_rest_api.files_api.id
  resource_id   = aws_api_gateway_resource.files_resource.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda_integration" {
  rest_api_id             = aws_api_gateway_rest_api.files_api.id
  resource_id             = aws_api_gateway_resource.files_resource.id
  http_method             = aws_api_gateway_method.get_files_method.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = aws_lambda_function.list_files.invoke_arn
}

resource "aws_api_gateway_deployment" "files_api_deployment" {
  depends_on  = [aws_api_gateway_integration.lambda_integration]
  rest_api_id = aws_api_gateway_rest_api.files_api.id
  stage_name  = "dev"
}

resource "aws_lambda_permission" "api_gateway_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.list_files.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.files_api.execution_arn}/*/*"
}

output "api_url" {
  value = "https://${aws_api_gateway_rest_api.files_api.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/dev/files"
}
