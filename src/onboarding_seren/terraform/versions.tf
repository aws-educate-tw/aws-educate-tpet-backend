terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }

    local = {
      source  = "hashicorp/local"
      version = "~> 2.5.1"
    }

    docker = {
      source  = "kreuzwerker/docker"
      version = ">= 3.0.2"
    }
  }
}