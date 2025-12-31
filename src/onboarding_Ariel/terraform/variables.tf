variable "aws_region" {
  type    = string
  default = "us-west-2" 
}

variable "environment" {
  type    = string
  default = "local-dev" 
}

variable "service_underscore" {
  type    = string
  default = "onboarding_ariel"
}


variable "lambda_architecture" {
  description = "Lambda architecture"
  type        = string
  default     = "x86_64"
}

variable "image_uri" {
  description = "ECR image URI for Lambda"
  type        = string
}
