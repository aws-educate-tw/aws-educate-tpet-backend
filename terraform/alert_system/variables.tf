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

variable "slack_workspace_id" {
  description = "Slack Workspace ID for AWS Chatbot (must be linked to Amazon Q Developer in Chat Applications first)"
  type        = string
  default     = "T072MQUJ3D5"
}

variable "slack_channel_id" {
  description = "Slack Channel ID for aws-alert"
  type        = string
  default     = "C0A1LLE15F1"
}

variable "slack_app_id" {
  description = "The Slack App ID for the alert bot"
  type        = string
  default     = "A0A6EQGPVFY"
}

variable "slack_client_id" {
  description = "The Slack Client ID for the alert bot"
  type        = string
  default     = "7089844615447.10218832811542"
}

variable "create_sns_topic" {
  description = "Whether to create a new SNS topic or use existing one"
  type        = bool
  default     = false
}
