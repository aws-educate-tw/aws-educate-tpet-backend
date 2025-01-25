resource "aws_ssm_parameter" "lambda_authorizer_lambda_invoke_arn" {
  name  = "${var.environment}-lambda_authorizer_lambda_invoke_arn"
  type  = "String"
  value = module.lambda_authorizer_lambda.lambda_function_invoke_arn
}
