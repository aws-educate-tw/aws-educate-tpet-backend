data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  vpc_cidr = "10.2.0.0/16"
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.environment}-${var.database_name}-vpc"
  cidr = local.vpc_cidr

  azs = slice(data.aws_availability_zones.available.names, 0, 2)

  database_subnets = [
    for k in range(2) : cidrsubnet(local.vpc_cidr, 8, k)
  ]

  create_database_subnet_group       = true
  create_database_subnet_route_table = true
  enable_dns_hostnames               = true
  enable_dns_support                 = true

  tags = {
    Terraform = "true"
    Service   = var.service_underscore
  }
}
