data "aws_availability_zones" "available" {
  state = "available"
  # Filter to ensure we get AZs that support RDS
  filter {
    name   = "opt-in-status"
    values = ["opt-in-not-required"]
  }
}

locals {
  vpc_cidr = "10.2.0.0/16"
  # Ensure we have at least 2 AZs and take exactly 2 to guarantee distribution
  availability_zones = slice(sort(data.aws_availability_zones.available.names), 0, 2)
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.environment}-${var.database_name}-vpc"
  cidr = local.vpc_cidr

  # Explicitly use the 2 selected AZs to ensure subnet distribution
  azs = local.availability_zones

  # Create database subnets with explicit AZ mapping
  # This ensures each subnet is in a different AZ
  database_subnets = [
    cidrsubnet(local.vpc_cidr, 8, 0), # First AZ (e.g., us-west-2a)
    cidrsubnet(local.vpc_cidr, 8, 1), # Second AZ (e.g., us-west-2b)
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
