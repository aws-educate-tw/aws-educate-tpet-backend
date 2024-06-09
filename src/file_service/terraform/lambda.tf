data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../list_files"
  output_path = "${path.module}/list_files_function.zip"
}

resource "aws_lambda_function" "list_files" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "list_files"
  role             = aws_iam_role.lambda_exec_role.arn
  handler          = "list_files_function.lambda_handler"
  source_code_hash = filebase64sha256(data.archive_file.lambda_zip.output_path)
  runtime          = "python3.11"

  environment {
    variables = {
      TABLE_NAME = "file"
    }
  }
}

resource "aws_lambda_permission" "api_gateway_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.list_files.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.files_api.execution_arn}/*/*"
}
