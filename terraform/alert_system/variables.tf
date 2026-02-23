variable "aws_region" {
  description = "aws region"
}

variable "environment" {
  description = "Current environtment: prod(ap-northeast-1)/dev(us-east-1)/local-dev(us-west-2), default dev(us-east-1)"
}

variable "domain_name" {
  description = "Domain name, for example: example.com"
  default     = "aws-educate.tw"
}

variable "lambda_architecture" {
  description = "CPU architecture for container image"
  type        = string
  default     = "x86_64"
}

variable "aws_educate_domain" {
  description = "aws-educate.tw"
  type        = string
  default     = "aws-educate.tw"
}

variable "aws_educate_domain_dot_prefix" {
  description = ".aws-educate.tw"
  type        = string
  default     = ".aws-educate.tw"
}

variable "zone_id" {
  description = "The Route 53 Hosted Zone ID for the domain"
  type        = string
  default     = "Z07729212EE8WFR3NG5K0"
}

variable "create_sns_topic" {
  description = "Whether to create a new SNS topic or use existing one"
  type        = bool
  default     = false
}
