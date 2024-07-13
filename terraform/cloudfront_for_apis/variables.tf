variable "aws_region" {
  description = "aws region"
}

variable "environment" {
  description = "Current environtment: prod(ap-northeast-1)/dev(us-east-1)/local-dev(us-west-2), sometimes it will be global"
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

variable "api_gateway_origins" {
  description = "List of API Gateway domain names and their corresponding path patterns"
  type = list(object({
    domain_name  = string
    path_pattern = string
  }))
}
