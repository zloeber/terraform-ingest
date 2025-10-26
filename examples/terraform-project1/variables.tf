variable "aws_region" {
  description = "AWS region for resource deployment"
  type        = string
  default     = "us-east-2"
}

variable "project_name" {
  description = "Project name for resource naming and tagging"
  type        = string
  default     = "ticketstoheaven"
}

variable "environment" {
  description = "Environment name (e.g., prod, staging, dev)"
  type        = string
  default     = "prod"
}

variable "domain_name" {
  description = "Domain name for the website"
  type        = string
}

variable "lambda_memory_size" {
  description = "Memory size for Lambda function in MB"
  type        = number
  default     = 512
  validation {
    condition     = var.lambda_memory_size >= 128 && var.lambda_memory_size <= 10240
    error_message = "Lambda memory must be between 128 and 10240 MB."
  }
}

variable "lambda_timeout" {
  description = "Timeout for Lambda function in seconds"
  type        = number
  default     = 30
  validation {
    condition     = var.lambda_timeout >= 1 && var.lambda_timeout <= 900
    error_message = "Lambda timeout must be between 1 and 900 seconds."
  }
}

variable "dynamodb_billing_mode" {
  description = "DynamoDB billing mode (PROVISIONED or PAY_PER_REQUEST)"
  type        = string
  default     = "PAY_PER_REQUEST"
  validation {
    condition     = contains(["PROVISIONED", "PAY_PER_REQUEST"], var.dynamodb_billing_mode)
    error_message = "Billing mode must be either PROVISIONED or PAY_PER_REQUEST."
  }
}

variable "enable_cloudwatch_logging" {
  description = "Enable CloudWatch logging for all services"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

variable "stripe_api_key_secret_name" {
  description = "Name of the secret in Secrets Manager for Stripe API key"
  type        = string
  default     = "ticketstoheaven/stripe-api-key"
}

variable "third_party_api_key_secret_name" {
  description = "Name of the secret in Secrets Manager for third-party API key"
  type        = string
  default     = "ticketstoheaven/third-party-api-key"
}

variable "third_party_api_endpoint_param_name" {
  description = "Name of the parameter in Parameter Store for third-party API endpoint"
  type        = string
  default     = "/ticketstoheaven/third-party-api-endpoint"
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}
