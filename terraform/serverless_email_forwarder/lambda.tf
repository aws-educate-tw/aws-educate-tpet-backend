resource "aws_lambda_function" "aws_educate_tpet_lambda" {
  function_name    = "forward_email"
  role            = aws_iam_role.aws_educate_tpet_lambda_role.arn
  runtime         = "python3.11"
  architectures = ["x86_64"]
  handler         = "lambda_function.lambda_handler"

  memory_size = 512
  timeout     = 60

  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.aws_educate_tpet_email_bucket.name
    }
  }
}

resource "aws_iam_role" "aws_educate_tpet_lambda_role" {
  name = "lambda_execution_role"
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
}

resource "aws_iam_policy" "aws_educate_tpet_lambda_policy" {
  name        = "lambda_s3_ses_policy"
  description = "Allow Lambda to access S3 and send emails via SES"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudwatchLogsAccess"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      },
      {
        Sid    = "S3Access"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "${aws_s3_bucket.aws_educate_tpet_email_bucket.arn}",
          "${aws_s3_bucket.aws_educate_tpet_email_bucket.arn}/*"
        ]
      },
      {
        Sid    = "SESAccess"
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Resource = aws_ses_domain_identity.ses_aws_educate_tpet.arn
      }
    ]
  })
}

resource "aws_iam_policy_attachment" "aws_educate_tpet_lambda_policy_attachment" {
  name       = "aws_educate_tpet_lambda_policy_attachment"
  roles      = [aws_iam_role.aws_educate_tpet_lambda_role.name]
  policy_arn = aws_iam_policy.aws_educate_tpet_lambda_policy.arn
}