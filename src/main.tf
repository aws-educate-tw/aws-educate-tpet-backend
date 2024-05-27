provider "aws" {
  region  = "ap-northeast-1"
  profile = "my-profile"
}

# Create S3 bucket for file upload
resource "aws_s3_bucket" "file_upload_bucket" {
  bucket = "email-sender-html-template"
  acl    = "private"

  tags = {
    Name        = "file-upload-bucket"
    Environment = "Dev"
  }
}

# Separate S3 bucket versioning resource
resource "aws_s3_bucket_versioning" "file_upload_bucket_versioning" {
  bucket = aws_s3_bucket.file_upload_bucket.bucket
  versioning_configuration {
    status = "Enabled"
  }
}

# IAM role setup for Lambda function
resource "aws_iam_role" "lambda_exec_role" {
  name = "lambda_upload_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },
    ]
  })

  inline_policy {
    name = "lambda_s3_policy"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Effect   = "Allow"
          Action   = ["s3:PutObject", "s3:GetObject"]
          Resource = ["arn:aws:s3:::email-sender-html-template/*"]
        },
      ]
    })
  }
}

# Archive the Lambda function code
data "archive_file" "lambda_function" {
  type        = "zip"
  source_file = "lambda_function.py"  
  output_path = "lambda_function.zip"
}

# Create the Lambda function
resource "aws_lambda_function" "generate_presigned_url" {
  function_name = "generate_presigned_url"
  role          = aws_iam_role.lambda_exec_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.11"
  source_code_hash = filebase64sha256(data.archive_file.lambda_function.output_path)
  filename      = data.archive_file.lambda_function.output_path

  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.file_upload_bucket.bucket
    }
  }
}

# Create the API Gateway REST API
resource "aws_api_gateway_rest_api" "upload_api" {
  name        = "upload_api"
  description = "API for generating presigned URLs"
}

# Create the /upload resource in API Gateway
resource "aws_api_gateway_resource" "upload" {
  rest_api_id = aws_api_gateway_rest_api.upload_api.id
  parent_id   = aws_api_gateway_rest_api.upload_api.root_resource_id
  path_part   = "upload"
}

# Set up the POST method for the /upload resource
resource "aws_api_gateway_method" "post_upload" {
  rest_api_id   = aws_api_gateway_rest_api.upload_api.id
  resource_id   = aws_api_gateway_resource.upload.id
  http_method   = "POST"
  authorization = "NONE"
}

# Integrate the POST method with the Lambda function
resource "aws_api_gateway_integration" "lambda_integration" {
  rest_api_id             = aws_api_gateway_rest_api.upload_api.id
  resource_id             = aws_api_gateway_resource.upload.id
  http_method             = aws_api_gateway_method.post_upload.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = "arn:aws:apigateway:ap-northeast-1:lambda:path/2015-03-31/functions/${aws_lambda_function.generate_presigned_url.arn}/invocations"
}

# Grant API Gateway permission to invoke the Lambda function
resource "aws_lambda_permission" "api_gateway_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.generate_presigned_url.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.upload_api.execution_arn}/*/*"
}

# Create API Gateway deployment
resource "aws_api_gateway_deployment" "upload_api_deployment" {
  rest_api_id = aws_api_gateway_rest_api.upload_api.id
  stage_name  = "dev"

  depends_on = [aws_api_gateway_integration.lambda_integration]
}

# Print the API Gateway URL
output "api_gateway_url" {
  value = aws_api_gateway_deployment.upload_api_deployment.invoke_url
  description = "URL of the API Gateway for uploading files"
}
