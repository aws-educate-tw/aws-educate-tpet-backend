variable "ses_email_identity" {
  description = "The name of the S3 bucket"
  type        = string
  default     = "awseducate.cloudambassador@gmail.com"
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

variable "bucket_name" {
  description = "The name of the S3 bucket"
  type        = string
  default     = "prod-aws-educate-tpet-email-bucket" 
}

variable "dev_email" {
  description = "The email address for dev"
  type        = string
  default     = "dev@aws-educate.tw"
}

variable "mkt_email" {
  description = "The email address for mkt"
  type        = string
  default     = "mkt@aws-educate.tw"
}

variable "event_email" {
  description = "The email address for event"
  type        = string
  default     = "event@aws-educate.tw"
}

variable "group1_email" {
  description = "The email address for group1"
  type        = string
  default     = "group1@aws-educate.tw"
}

variable "group2_email" {
  description = "The email address for group2"
  type        = string
  default     = "group2@aws-educate.tw"
}

variable "group3_email" {
  description = "The email address for group3"
  type        = string
  default     = "group3@aws-educate.tw"
}