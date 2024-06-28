variable "aws_region" {
  description = "aws region"
}

variable "environment" {
  description = "Current environtment: prod(ap-northeast-1)/dev(us-east-1)/local-dev(us-west-2), default dev(us-east-1)"
}

variable "bucket_name" {
  description = "The name of the S3 bucket"
}
