output "api_url" {
  value = "https://${aws_api_gateway_rest_api.files_api.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/dev/files"
}
