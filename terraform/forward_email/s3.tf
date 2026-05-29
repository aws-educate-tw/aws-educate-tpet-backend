# event trigger for s3 bucket
resource "aws_s3_bucket_notification" "s3_event_trigger" {
  bucket = local.bucket_name

  lambda_function {
    id                  = "forward_email"
    lambda_function_arn = module.forward_email_lambda.lambda_function_arn
    events              = ["s3:ObjectCreated:*"]
  }

  depends_on = [
    aws_lambda_permission.allow_s3_invoke_aws_educate_tpet_lambda
  ]
}

# allow s3 to invoke lambda
resource "aws_lambda_permission" "allow_s3_invoke_aws_educate_tpet_lambda" {
  statement_id  = "AllowS3InvokeLambda"
  action        = "lambda:InvokeFunction"
  function_name = module.forward_email_lambda.lambda_function_name
  principal     = "s3.amazonaws.com"
  source_arn    = "arn:aws:s3:::${local.bucket_name}"
}