provider "aws" {
  region  = "ap-northeast-1"
  profile = "my-profile"
}

# Create S3 bucket for file upload
resource "aws_s3_bucket" "file_upload_bucket" {
  bucket = "email-sender-excel"

  tags = {
    Name        = "file-upload-bucket"
    Environment = "Dev"
    Creator     = "Richie"
  }
}

# Separate S3 bucket versioning resource
resource "aws_s3_bucket_versioning" "file_upload_bucket_versioning" {
  bucket = aws_s3_bucket.file_upload_bucket.bucket
  versioning_configuration {
    status = "Enabled"
  }
}

# Create DynamoDB
resource "aws_dynamodb_table" "file_metadata_table" {
  name           = "file"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "file_id"
  attribute {
    name = "file_id"
    type = "S"
  }

  tags = {
    Creator = "Richie"
  }
}

# IAM role setup for Lambda function
resource "aws_iam_role" "lambda_exec_role" {
  name = "lambda-upload-role"
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
    name = "lambda_s3_dynamodb_policy"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Effect   = "Allow"
          Action   = ["s3:PutObject", "s3:GetObject"]
          Resource = ["arn:aws:s3:::email-sender-excel/*"]
        },
        {
          Effect   = "Allow"
          Action   = [
            "dynamodb:PutItem",
            "dynamodb:UpdateItem",
            "dynamodb:GetItem",
            "dynamodb:Query",
            "dynamodb:Scan"
          ]
          Resource = [
            "arn:aws:dynamodb:ap-northeast-1:*:table/file",
            "arn:aws:dynamodb:ap-northeast-1:*:table/file/index/file_name_index"
          ]
        },
        {
          Effect   = "Allow"
          Action   = [
            "logs:CreateLogGroup",
            "logs:CreateLogStream",
            "logs:PutLogEvents"
          ]
          Resource = "arn:aws:logs:*:*:*"
        }
      ]
    })
  }

  tags = {
    Creator = "Richie"
  }
}

# Archive the Lambda function code
data "archive_file" "lambda_function" {
  type        = "zip"
  source_file = "lambda_function.py"
  output_path = "lambda_function.zip"
}

# Create the Lambda function
resource "aws_lambda_function" "email_sender_upload_file" {
  function_name = "email-sender-upload-file"
  role          = aws_iam_role.lambda_exec_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.11"
  source_code_hash = filebase64sha256(data.archive_file.lambda_function.output_path)
  filename      = data.archive_file.lambda_function.output_path

  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.file_upload_bucket.bucket
      TABLE_NAME  = aws_dynamodb_table.file_metadata_table.name
    }
  }

  tags = {
    Creator = "Richie"
  }
}

# Create the API Gateway REST API
resource "aws_api_gateway_rest_api" "email_sender_upload_file_api" {
  name        = "upload-file"
  description = "API for direct file upload to S3"

  tags = {
    Creator = "Richie"
  }
}

# Create the /upload-file resource in API Gateway
resource "aws_api_gateway_resource" "upload_resource" {
  rest_api_id = aws_api_gateway_rest_api.email_sender_upload_file_api.id
  parent_id   = aws_api_gateway_rest_api.email_sender_upload_file_api.root_resource_id
  path_part   = "upload-file"
}

# Set up the POST method for the /upload resource
resource "aws_api_gateway_method" "post_upload_method" {
  rest_api_id   = aws_api_gateway_rest_api.email_sender_upload_file_api.id
  resource_id   = aws_api_gateway_resource.upload_resource.id
  http_method   = "POST"
  authorization = "NONE"
}

# Integrate the POST method with the Lambda function
resource "aws_api_gateway_integration" "lambda_integration" {
  rest_api_id             = aws_api_gateway_rest_api.email_sender_upload_file_api.id
  resource_id             = aws_api_gateway_resource.upload_resource.id
  http_method             = aws_api_gateway_method.post_upload_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = "arn:aws:apigateway:ap-northeast-1:lambda:path/2015-03-31/functions/${aws_lambda_function.email_sender_upload_file.arn}/invocations"
}

# API Gateway permission to invoke the Lambda function
resource "aws_lambda_permission" "api_gateway_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.email_sender_upload_file.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.email_sender_upload_file_api.execution_arn}/*/*"
}

# Create API Gateway deployment
resource "aws_api_gateway_deployment" "upload_api_deployment" {
  rest_api_id = aws_api_gateway_rest_api.email_sender_upload_file_api.id
  stage_name  = "dev"

  depends_on = [aws_api_gateway_integration.lambda_integration]
}

# Print the API Gateway URL
output "api_gateway_url" {
  value       = aws_api_gateway_deployment.upload_api_deployment.invoke_url
  description = "URL of the API Gateway for uploading files"
}
