variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Deployment Environment (production / staging / dev)"
  type        = string
  default     = "production"
}

variable "app_name" {
  description = "Name prefix for aws resource"
  type        = string
  default     = "multi-agent-research"
}

variable "s3_bucket_name" {
  description = "Globally unique name for AWS S3 PDF and report storage bucket"
  type        = string
  default     = "multi-agent-research-pdf-bucket-233171357958"
}
