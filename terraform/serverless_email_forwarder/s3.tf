resource "aws_s3_bucket" "aws_educate_tpet_email_bucket" {
  bucket = var.bucket_name
  acl    = "private"
}

# event trigger for s3 bucket
resource "aws_s3_bucket_notification" "s3_event_trigger" {
  bucket = aws_s3_bucket.aws_educate_tpet_email_bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.aws_educate_tpet_lambda.arn
    events             = ["s3:ObjectCreated:*"]
  }
}

# allow ses to put object in s3 bucket
resource "aws_s3_bucket_policy" "ses_put_object" {
  bucket = aws_s3_bucket.aws_educate_tpet_email_bucket.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowSESPutObject"
        Effect    = "Allow"
        Principal = {
          Service = "ses.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.aws_educate_tpet_email_bucket.arn}/*" # "arn:aws:s3:::prod-aws-educate-tpet-email-bucket/*"
        Condition = {
          StringEquals = {
            "aws:Referer" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
}

# allow s3 to invoke lambda
resource "aws_lambda_permission" "allow_s3_invoke_aws_educate_tpet_lambda" {
  statement_id  = "AllowS3InvokeLambda"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.aws_educate_tpet_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.aws_educate_tpet_email_bucket.arn
}
