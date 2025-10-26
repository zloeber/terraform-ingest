locals {
  common_tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      CreatedAt   = "2025-10-25"
    },
    var.tags
  )

  # Standardized resource naming
  name_prefix = "${var.project_name}-${var.environment}"
  
  # Lambda configuration
  order_processing_lambda_name   = "${local.name_prefix}-order-processing"
  webhook_handler_lambda_name    = "${local.name_prefix}-webhook-handler"
  
  # API Gateway
  api_gateway_name = "${local.name_prefix}-api"
  
  # DynamoDB tables
  orders_table_name    = "${local.name_prefix}-orders"
  customers_table_name = "${local.name_prefix}-customers"
  payments_table_name  = "${local.name_prefix}-payments"
  
  # S3 buckets
  website_bucket_name = "${var.project_name}-website-${data.aws_caller_identity.current.account_id}"
  
  # CloudFront
  cloudfront_distribution_name = "${local.name_prefix}-cdn"
  
  # CloudWatch log groups
  lambda_log_group_prefix    = "/aws/lambda/${local.name_prefix}"
  api_gateway_log_group_name = "/aws/apigateway/${local.name_prefix}"
  
  # IAM roles
  lambda_role_name       = "${local.name_prefix}-lambda-role"
  api_gateway_role_name  = "${local.name_prefix}-api-gateway-role"
}

data "aws_caller_identity" "current" {}

data "aws_region" "current" {
  provider = aws
}
