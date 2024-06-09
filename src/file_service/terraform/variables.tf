variable "cors_allow_origin" {
  description = "The origin that is allowed to access the API"
  type        = string
  default     = "*"
}

variable "environment" {
  description = "The environment to deploy the service to"
  type        = string
  default     = "dev"
}
