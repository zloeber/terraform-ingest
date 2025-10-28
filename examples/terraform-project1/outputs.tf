output "cloudfront_distribution_domain_name" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.website.domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.website.id
}

output "s3_website_bucket_name" {
  description = "S3 bucket name for website assets"
  value       = aws_s3_bucket.website.id
}

output "api_gateway_invoke_url" {
  description = "API Gateway stage invoke URL"
  value       = aws_api_gateway_stage.orders_api_stage.invoke_url
}

output "api_gateway_rest_api_id" {
  description = "API Gateway REST API ID"
  value       = aws_api_gateway_rest_api.orders_api.id
}

output "orders_table_name" {
  description = "DynamoDB Orders table name"
  value       = aws_dynamodb_table.orders.name
}

output "customers_table_name" {
  description = "DynamoDB Customers table name"
  value       = aws_dynamodb_table.customers.name
}

output "payments_table_name" {
  description = "DynamoDB Payments table name"
  value       = aws_dynamodb_table.payments.name
}

output "order_processing_lambda_arn" {
  description = "ARN of the Order Processing Lambda function"
  value       = aws_lambda_function.order_processing.arn
}

output "order_processing_lambda_name" {
  description = "Name of the Order Processing Lambda function"
  value       = aws_lambda_function.order_processing.function_name
}

output "webhook_handler_lambda_arn" {
  description = "ARN of the Webhook Handler Lambda function"
  value       = aws_lambda_function.webhook_handler.arn
}

output "webhook_handler_lambda_name" {
  description = "Name of the Webhook Handler Lambda function"
  value       = aws_lambda_function.webhook_handler.function_name
}

output "stripe_secret_arn" {
  description = "ARN of the Stripe API Key secret"
  value       = aws_secretsmanager_secret.stripe_api_key.arn
  sensitive   = true
}

output "third_party_api_secret_arn" {
  description = "ARN of the Third-Party API Key secret"
  value       = aws_secretsmanager_secret.third_party_api_key.arn
  sensitive   = true
}

output "lambda_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_role.arn
}

output "lambda_role_name" {
  description = "Name of the Lambda execution role"
  value       = aws_iam_role.lambda_role.name
}

output "cloudwatch_log_group_lambda" {
  description = "CloudWatch log group for Lambda functions"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}

output "cloudwatch_log_group_api_gateway" {
  description = "CloudWatch log group for API Gateway"
  value       = aws_cloudwatch_log_group.api_gateway_logs.name
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}

output "project_name" {
  description = "Project name"
  value       = var.project_name
}

output "region" {
  description = "AWS region"
  value       = var.aws_region
}
