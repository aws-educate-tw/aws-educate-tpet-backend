terraform {
  required_version = "~> 1.14.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.36.0, < 7.0.0"
    }

    local = {
      source  = "hashicorp/local"
      version = "~> 2.5.1"
    }

    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.6.2"
    }
  }
}
