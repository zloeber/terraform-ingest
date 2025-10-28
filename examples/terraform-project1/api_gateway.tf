# API Gateway REST API
resource "aws_api_gateway_rest_api" "orders_api" {
  name        = local.api_gateway_name
  description = "REST API for TicketsToHeaven order processing"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = merge(
    local.common_tags,
    {
      Name        = local.api_gateway_name
      Description = "Order processing API"
    }
  )
}

# CloudWatch Log Group for API Gateway
resource "aws_cloudwatch_log_group" "api_gateway_log_group" {
  name              = local.api_gateway_log_group_name
  retention_in_days = var.log_retention_days

  tags = local.common_tags
}

# Account-level API Gateway settings for logging
resource "aws_api_gateway_account" "api_account" {
  cloudwatch_role_arn = aws_iam_role.api_gateway_cloudwatch_role.arn
}

# Resource: /orders (POST - create order)
resource "aws_api_gateway_resource" "orders" {
  rest_api_id = aws_api_gateway_rest_api.orders_api.id
  parent_id   = aws_api_gateway_rest_api.orders_api.root_resource_id
  path_part   = "orders"
}

# Method: POST /orders
resource "aws_api_gateway_method" "create_order" {
  rest_api_id      = aws_api_gateway_rest_api.orders_api.id
  resource_id      = aws_api_gateway_resource.orders.id
  http_method      = "POST"
  authorization    = "NONE"
  request_validator_id = aws_api_gateway_request_validator.body_validator.id

  request_models = {
    "application/json" = aws_api_gateway_model.order_model.name
  }
}

# Integration: POST /orders with Lambda
resource "aws_api_gateway_integration" "create_order_integration" {
  rest_api_id      = aws_api_gateway_rest_api.orders_api.id
  resource_id      = aws_api_gateway_resource.orders.id
  http_method      = aws_api_gateway_method.create_order.http_method
  type             = "AWS_PROXY"
  integration_http_method = "POST"
  uri              = aws_lambda_function.order_processing.invoke_arn
}

# Method Response for POST /orders
resource "aws_api_gateway_method_response" "create_order_response" {
  rest_api_id = aws_api_gateway_rest_api.orders_api.id
  resource_id = aws_api_gateway_resource.orders.id
  http_method = aws_api_gateway_method.create_order.http_method
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }
}

# Integration Response for POST /orders
resource "aws_api_gateway_integration_response" "create_order_integration_response" {
  rest_api_id      = aws_api_gateway_rest_api.orders_api.id
  resource_id      = aws_api_gateway_resource.orders.id
  http_method      = aws_api_gateway_method.create_order.http_method
  status_code      = aws_api_gateway_method_response.create_order_response.status_code
  selection_pattern = ""
}

# Lambda permission for API Gateway to invoke order processing Lambda
resource "aws_lambda_permission" "api_gateway_order_processing" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.order_processing.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.orders_api.execution_arn}/*/*"
}

# Resource: /webhooks/stripe (POST - handle Stripe webhooks)
resource "aws_api_gateway_resource" "webhooks" {
  rest_api_id = aws_api_gateway_rest_api.orders_api.id
  parent_id   = aws_api_gateway_rest_api.orders_api.root_resource_id
  path_part   = "webhooks"
}

resource "aws_api_gateway_resource" "webhooks_stripe" {
  rest_api_id = aws_api_gateway_rest_api.orders_api.id
  parent_id   = aws_api_gateway_resource.webhooks.id
  path_part   = "stripe"
}

# Method: POST /webhooks/stripe
resource "aws_api_gateway_method" "stripe_webhook" {
  rest_api_id   = aws_api_gateway_rest_api.orders_api.id
  resource_id   = aws_api_gateway_resource.webhooks_stripe.id
  http_method   = "POST"
  authorization = "NONE"
}

# Integration: POST /webhooks/stripe with Lambda
resource "aws_api_gateway_integration" "stripe_webhook_integration" {
  rest_api_id             = aws_api_gateway_rest_api.orders_api.id
  resource_id             = aws_api_gateway_resource.webhooks_stripe.id
  http_method             = aws_api_gateway_method.stripe_webhook.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = aws_lambda_function.webhook_handler.invoke_arn
}

# Method Response for POST /webhooks/stripe
resource "aws_api_gateway_method_response" "stripe_webhook_response" {
  rest_api_id = aws_api_gateway_rest_api.orders_api.id
  resource_id = aws_api_gateway_resource.webhooks_stripe.id
  http_method = aws_api_gateway_method.stripe_webhook.http_method
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }
}

# Integration Response for POST /webhooks/stripe
resource "aws_api_gateway_integration_response" "stripe_webhook_integration_response" {
  rest_api_id      = aws_api_gateway_rest_api.orders_api.id
  resource_id      = aws_api_gateway_resource.webhooks_stripe.id
  http_method      = aws_api_gateway_method.stripe_webhook.http_method
  status_code      = aws_api_gateway_method_response.stripe_webhook_response.status_code
  selection_pattern = ""
}

# Lambda permission for API Gateway to invoke webhook handler Lambda
resource "aws_lambda_permission" "api_gateway_webhook_handler" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.webhook_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.orders_api.execution_arn}/*/*"
}

# Request Validator for validating JSON payloads
resource "aws_api_gateway_request_validator" "body_validator" {
  rest_api_id           = aws_api_gateway_rest_api.orders_api.id
  name                  = "body-validator"
  validate_request_body = true
  validate_request_parameters = false
}

# Model for order request validation
resource "aws_api_gateway_model" "order_model" {
  rest_api_id  = aws_api_gateway_rest_api.orders_api.id
  name         = "OrderModel"
  content_type = "application/json"

  schema = jsonencode({
    type = "object"
    properties = {
      customer_id = {
        type = "string"
      }
      items = {
        type = "array"
        items = {
          type = "object"
          properties = {
            product_id = { type = "string" }
            quantity   = { type = "integer" }
            price      = { type = "number" }
          }
          required = ["product_id", "quantity", "price"]
        }
      }
      total_amount = {
        type = "number"
      }
    }
    required = ["customer_id", "items", "total_amount"]
  })
}

# API Gateway Deployment
resource "aws_api_gateway_deployment" "orders_api_deployment" {
  depends_on = [
    aws_api_gateway_integration.create_order_integration,
    aws_api_gateway_integration.stripe_webhook_integration,
  ]

  rest_api_id = aws_api_gateway_rest_api.orders_api.id
}

# API Stage with logging
resource "aws_api_gateway_stage" "orders_api_stage" {
  deployment_id = aws_api_gateway_deployment.orders_api_deployment.id
  rest_api_id   = aws_api_gateway_rest_api.orders_api.id
  stage_name    = var.environment

  # CloudWatch Logs configuration
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway_log_group.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      resourcePath   = "$context.resourcePath"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
      error          = "$context.error.message"
      integrationLatency = "$context.integration.latency"
    })
  }

  tags = local.common_tags
}
