provider "aws" {
  region  = "ap-northeast-1"
  profile = "my-profile"
}

variable "aws_region" {
  default = "ap-northeast-1"
}



resource "aws_iam_role" "lambda_role" {
  name = "lambda_execution_role"
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Action" : "sts:AssumeRole",
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Creator = "Richie"
  }
}

resource "aws_iam_policy" "ecr_policy" {
  name = "ECRPolicy"
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : [
          "ecr:BatchCheckLayerAvailability",
          "ecr:CompleteLayerUpload",
          "ecr:GetDownloadUrlForLayer",
          "ecr:InitiateLayerUpload",
          "ecr:PutImage",
          "ecr:UploadLayerPart"
        ],
        "Resource" : "arn:aws:ecr:ap-northeast-1:070576557102:repository/email-sender-repo"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attach_ecr_policy" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.ecr_policy.arn
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "lambda_policy"
  role = aws_iam_role.lambda_role.id
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        "Resource" : "arn:aws:logs:*:*:*"
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "s3:GetObject"
        ],
        "Resource" : "arn:aws:s3:::email-sender-excel/*"
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "ses:SendEmail"
        ],
        "Resource" : "*"
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "dynamodb:PutItem"
        ],
        "Resource" : "arn:aws:dynamodb:${var.aws_region}:*:table/email"
      }
    ]
  })
}

resource "aws_ecr_repository" "email_sender_repo" {
  name = "email-sender-repo"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name    = "email-sender-repo"
    Creator = "Richie"
  }
}

data "aws_ecr_authorization_token" "ecr" {}

resource "null_resource" "docker_image" {
  provisioner "local-exec" {
    command = <<EOT
      set -ex
      aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${data.aws_ecr_authorization_token.ecr.proxy_endpoint}
      docker build -t email-sender .
      docker images 
      docker tag email-sender:latest ${aws_ecr_repository.email_sender_repo.repository_url}:latest
      docker push ${aws_ecr_repository.email_sender_repo.repository_url}:latest
    EOT
  }
}

resource "aws_lambda_function" "email_sender" {
  function_name = "email-sender"
  role          = aws_iam_role.lambda_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.email_sender_repo.repository_url}:latest"

  environment {
    variables = {
      BUCKET_NAME    = "email-sender-excel"
      DYNAMODB_TABLE = "email"
    }
  }

  tags = {
    Creator = "Richie"
  }

  depends_on = [
    null_resource.docker_image
  ]
}

resource "aws_api_gateway_rest_api" "api" {
  name = "EmailSenderAPI"

  tags = {
    Creator = "Richie"
  }
}

resource "aws_api_gateway_resource" "resource" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "send-email"
}

resource "aws_api_gateway_method" "method" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.resource.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "integration" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.resource.id
  http_method             = aws_api_gateway_method.method.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = aws_lambda_function.email_sender.invoke_arn
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.email_sender.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/*"
}

resource "aws_api_gateway_deployment" "upload_api_deployment" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  stage_name  = "dev"

  depends_on = [
    aws_api_gateway_integration.integration,
    aws_lambda_permission.api_gateway
  ]
}

output "api_gateway_url" {
  value       = aws_api_gateway_deployment.upload_api_deployment.invoke_url
  description = "URL of the API Gateway for uploading files"
}
