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
  default     = "aws-educate.tw"
}

variable "dynamodb_table" {
  description = "Current service's DynamoDB table name"
}

variable "dynamodb_table_total_count" {
  description = "Current service's DynamoDB table for total count"

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
  default     = "x86_64"
}
