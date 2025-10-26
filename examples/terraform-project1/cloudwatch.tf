# CloudWatch Log Group for Lambda functions
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "${local.lambda_log_group_prefix}-general"
  retention_in_days = var.log_retention_days

  tags = merge(
    local.common_tags,
    {
      Name = "${local.lambda_log_group_prefix}-general"
    }
  )
}

# CloudWatch Log Group for Order Processing Lambda
resource "aws_cloudwatch_log_group" "order_processing_lambda_logs" {
  name              = "${local.lambda_log_group_prefix}-order-processing"
  retention_in_days = var.log_retention_days

  tags = merge(
    local.common_tags,
    {
      Name = "${local.lambda_log_group_prefix}-order-processing"
    }
  )
}

# CloudWatch Log Group for Webhook Handler Lambda
resource "aws_cloudwatch_log_group" "webhook_handler_lambda_logs" {
  name              = "${local.lambda_log_group_prefix}-webhook-handler"
  retention_in_days = var.log_retention_days

  tags = merge(
    local.common_tags,
    {
      Name = "${local.lambda_log_group_prefix}-webhook-handler"
    }
  )
}

# CloudWatch Log Group for API Gateway
resource "aws_cloudwatch_log_group" "api_gateway_logs" {
  name              = local.api_gateway_log_group_name
  retention_in_days = var.log_retention_days

  tags = merge(
    local.common_tags,
    {
      Name = local.api_gateway_log_group_name
    }
  )
}

# CloudWatch Metric Alarm for Lambda Errors - Order Processing
resource "aws_cloudwatch_metric_alarm" "lambda_errors_order_processing" {
  alarm_name          = "${local.order_processing_lambda_name}-errors"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "Alert when Order Processing Lambda has errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.order_processing.function_name
  }

  tags = local.common_tags
}

# CloudWatch Metric Alarm for Lambda Errors - Webhook Handler
resource "aws_cloudwatch_metric_alarm" "lambda_errors_webhook_handler" {
  alarm_name          = "${local.webhook_handler_lambda_name}-errors"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "Alert when Webhook Handler Lambda has errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.webhook_handler.function_name
  }

  tags = local.common_tags
}

# CloudWatch Metric Alarm for Lambda Throttling
resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  alarm_name          = "${local.name_prefix}-lambda-throttles"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "Alert when any Lambda function is throttled"
  treat_missing_data  = "notBreaching"

  tags = local.common_tags
}

# CloudWatch Metric Alarm for DynamoDB Orders Read Throttling
resource "aws_cloudwatch_metric_alarm" "dynamodb_orders_read_throttle" {
  alarm_name          = "${local.orders_table_name}-read-throttle"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = "ReadThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "Alert when Orders table has read throttling"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.orders.name
  }

  tags = local.common_tags
}

# CloudWatch Metric Alarm for DynamoDB Orders Write Throttling
resource "aws_cloudwatch_metric_alarm" "dynamodb_orders_write_throttle" {
  alarm_name          = "${local.orders_table_name}-write-throttle"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = "WriteThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "Alert when Orders table has write throttling"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.orders.name
  }

  tags = local.common_tags
}
