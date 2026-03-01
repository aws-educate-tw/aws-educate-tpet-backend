terraform {
  required_version = "~> 1.14.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.34.0"
    }

    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0.2"
    }
  }
}
