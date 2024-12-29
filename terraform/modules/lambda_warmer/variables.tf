# Required variables
variable "aws_region" {
  description = "AWS region where the Lambda warmer will be deployed."
}

variable "environment" {
  description = "Current environment: prod(ap-northeast-1)/dev(us-east-1)/local-dev(us-west-2), default dev(us-east-1)."
}

# Optional variables
variable "lambda_function_name" {
  description = "Name of the Lambda function used for prewarming."
  default     = "lambda-warmer"
}

variable "lambda_schedule_expression" {
  description = "EventBridge schedule expression for triggering the Lambda warmer. For example: rate(5 minutes)."
  default     = "rate(5 minutes)"
}

variable "scheduler_max_retry_attempts" {
  description = "Maximum retry attempts for the EventBridge scheduler target."
  type        = number
  default     = 0
}

variable "prewarm_tag_key" {
  description = "The tag key to identify functions that need prewarming"
  type        = string
  default     = "Prewarm"
}

variable "prewarm_tag_value" {
  description = "The expected value of the tag for functions that need prewarming"
  type        = string
  default     = "true"
}
