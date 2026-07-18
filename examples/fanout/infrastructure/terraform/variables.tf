variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region for the fan-out stack"
  type        = string
  default     = "us-east-1"
}
