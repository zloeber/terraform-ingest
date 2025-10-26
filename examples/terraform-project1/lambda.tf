# Placeholder Lambda function for order processing
# In production, this would be replaced with actual application code
resource "aws_lambda_function" "order_processing" {
  filename         = data.archive_file.lambda_placeholder.output_path
  function_name    = local.order_processing_lambda_name
  role             = aws_iam_role.lambda_role.arn
  handler          = "index.handler"
  runtime          = "nodejs18.x"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size
  source_code_hash = data.archive_file.lambda_placeholder.output_base64sha256

  environment {
    variables = {
      ORDERS_TABLE_NAME    = aws_dynamodb_table.orders.name
      CUSTOMERS_TABLE_NAME = aws_dynamodb_table.customers.name
      PAYMENTS_TABLE_NAME  = aws_dynamodb_table.payments.name
      STRIPE_SECRET_NAME   = var.stripe_api_key_secret_name
      THIRD_PARTY_SECRET   = var.third_party_api_key_secret_name
      THIRD_PARTY_ENDPOINT = var.third_party_api_endpoint_param_name
    }
  }

  tags = merge(
    local.common_tags,
    {
      Name        = local.order_processing_lambda_name
      Description = "Lambda function for processing orders"
    }
  )

  depends_on = [
    aws_iam_role_policy.lambda_cloudwatch_logs,
    aws_iam_role_policy.lambda_dynamodb_orders,
    aws_iam_role_policy.lambda_dynamodb_customers,
    aws_iam_role_policy.lambda_dynamodb_payments,
  ]
}

# Placeholder Lambda function for Stripe webhook handling
resource "aws_lambda_function" "webhook_handler" {
  filename         = data.archive_file.lambda_placeholder.output_path
  function_name    = local.webhook_handler_lambda_name
  role             = aws_iam_role.lambda_role.arn
  handler          = "index.handler"
  runtime          = "nodejs18.x"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size
  source_code_hash = data.archive_file.lambda_placeholder.output_base64sha256

  environment {
    variables = {
      ORDERS_TABLE_NAME   = aws_dynamodb_table.orders.name
      PAYMENTS_TABLE_NAME = aws_dynamodb_table.payments.name
      STRIPE_SECRET_NAME  = var.stripe_api_key_secret_name
    }
  }

  tags = merge(
    local.common_tags,
    {
      Name        = local.webhook_handler_lambda_name
      Description = "Lambda function for handling Stripe webhooks"
    }
  )

  depends_on = [
    aws_iam_role_policy.lambda_cloudwatch_logs,
    aws_iam_role_policy.lambda_dynamodb_orders,
    aws_iam_role_policy.lambda_dynamodb_payments,
  ]
}

# Archive for placeholder Lambda code
data "archive_file" "lambda_placeholder" {
  type        = "zip"
  output_path = "/tmp/lambda_placeholder.zip"

  source {
    content  = file("${path.module}/lambda_placeholder.js")
    filename = "index.js"
  }
}
