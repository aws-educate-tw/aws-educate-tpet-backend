variable "domain_name" {
  description = "The custom domain name for CloudFront"
  type        = string
  default     = "api.tpet.aws-educate.tw"
}


variable "acm_certificate_arn" {
  description = "The ARN of the ACM certificate for the custom domain"
  type        = string
  default     = "arn:aws:acm:us-east-1:070576557102:certificate/6ef7979c-596b-42fd-a6ed-fceccc2efc0b"
}

variable "zone_id" {
  description = "The Route 53 Hosted Zone ID for the domain"
  type        = string
  default     = "Z00402303DMA4KDX72AUO"
}

variable "api_gateway_origins" {
  description = "List of API Gateway domain names and their corresponding path patterns"
  type = list(object({
    domain_name  = string
    path_pattern = string
  }))
  default = [
    {
      # Campaign Service
      domain_name  = "pihjp3tc7f.execute-api.ap-northeast-1.amazonaws.com"
      path_pattern = "/dev/campaigns*"
    },
    {
      # File Service - List files & Get file by ID
      domain_name  = "8um2zizr80.execute-api.ap-northeast-1.amazonaws.com"
      path_pattern = "/dev/files*"
    },
    {
      # File Service - Upload file
      domain_name  = "ssckvgoo10.execute-api.ap-northeast-1.amazonaws.com"
      path_pattern = "/dev/upload-file*"
    },
    {
      # File Service - Upload multiple files
      domain_name  = "sojek1stci.execute-api.ap-northeast-1.amazonaws.com"
      path_pattern = "/dev/upload-multiple-file*"
    },

    {
      # Email Service - Send Email
      domain_name  = "diyf4tafbl.execute-api.ap-northeast-1.amazonaws.com"
      path_pattern = "/dev/send-email*"
    }

  ]
}


variable "aws_region" {
  description = "The AWS region to deploy the service to"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "The environment to deploy the service to"
  type        = string
  default     = "dev"

}
