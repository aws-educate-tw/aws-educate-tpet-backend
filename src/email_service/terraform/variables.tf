variable "aws_region" {
  description = "aws region"
}

variable "environment" {
  description = "Current environtment: prod(ap-northeast-1)/dev(us-east-1)/local-dev(us-west-2), default dev(us-east-1)"
}

variable "service_underscore" {
  description = "Current service name"
}

variable "service_hyphen" {
  description = "This variable contains the current service name, but with hyphens instead of underscores. For example: demo-service."
}
variable "domain_name" {
  description = "Domain name, for example: example.com"
}

variable "dynamodb_table" {
  description = "Current service's DynamoDB table name"
}

variable "run_dynamodb_table" {
  description = "Current service's Run DynamoDB table name"
}

variable "pagination_state_dynamodb_table" {
  description = "Current service's Pagination state DynamoDB table name"
}

variable "enable_pitr" {
  description = "Enable Point-In-Time Recovery for DynamoDB tables"
  type        = bool
}

variable "enable_deletion_protection_for_dynamodb_table" {
  description = "Enable deletion protection for DynamoDB tables"
  type        = bool
}

variable "lambda_architecture" {
  description = "CPU architecture for container image"
  type        = string
  default     = "arm64"
}
