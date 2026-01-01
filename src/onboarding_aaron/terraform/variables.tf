variable "aws_region" {
  description = "AWS region"
  default     = "us-west-2"
}

variable "environment" {
  description = "Current environment"
}

variable "lambda_architecture" {
  description = "CPU architecture for container image"
  type        = string
  default     = "x86_64"
}