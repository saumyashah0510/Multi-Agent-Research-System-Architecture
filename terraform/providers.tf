terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote State Storage in S3 + DynamoDB Locking
  backend "s3" {
    bucket       = "multi-agent-research-tfstate-233171357958"
    key          = "state/terraform.tfstate"
    region       = "ap-south-1"
    use_lockfile = true
    encrypt      = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "Multi-Agent Research Assistant"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
