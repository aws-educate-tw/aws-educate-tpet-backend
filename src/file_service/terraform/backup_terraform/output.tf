output "api_url" {
  description = "The URL of the API Gateway"
  value       = "https://${aws_api_gateway_rest_api.files_api.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/dev/files"
}

output "api_gateway_domain_name" {
  description = "The domain name of the API Gateway"
  value       = aws_api_gateway_rest_api.files_api.execution_arn
}
