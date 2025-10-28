# IAM Role for Lambda execution
resource "aws_iam_role" "lambda_role" {
  name               = local.lambda_role_name
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# IAM Policy for Lambda to write logs to CloudWatch
resource "aws_iam_role_policy" "lambda_cloudwatch_logs" {
  name   = "${local.lambda_role_name}-cloudwatch-logs"
  role   = aws_iam_role.lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/*"
      }
    ]
  })
}

# IAM Policy for Lambda to read/write to DynamoDB Orders table
resource "aws_iam_role_policy" "lambda_dynamodb_orders" {
  name   = "${local.lambda_role_name}-dynamodb-orders"
  role   = aws_iam_role.lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.orders.arn,
          "${aws_dynamodb_table.orders.arn}/index/*"
        ]
      }
    ]
  })
}

# IAM Policy for Lambda to read/write to DynamoDB Customers table
resource "aws_iam_role_policy" "lambda_dynamodb_customers" {
  name   = "${local.lambda_role_name}-dynamodb-customers"
  role   = aws_iam_role.lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.customers.arn,
          "${aws_dynamodb_table.customers.arn}/index/*"
        ]
      }
    ]
  })
}

# IAM Policy for Lambda to read/write to DynamoDB Payments table
resource "aws_iam_role_policy" "lambda_dynamodb_payments" {
  name   = "${local.lambda_role_name}-dynamodb-payments"
  role   = aws_iam_role.lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.payments.arn,
          "${aws_dynamodb_table.payments.arn}/index/*"
        ]
      }
    ]
  })
}

# IAM Policy for Lambda to read from Secrets Manager
resource "aws_iam_role_policy" "lambda_secrets_manager" {
  name   = "${local.lambda_role_name}-secrets-manager"
  role   = aws_iam_role.lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.stripe_api_key.arn,
          aws_secretsmanager_secret.third_party_api_key.arn
        ]
      }
    ]
  })
}

# IAM Policy for Lambda to read from Parameter Store
resource "aws_iam_role_policy" "lambda_parameter_store" {
  name   = "${local.lambda_role_name}-parameter-store"
  role   = aws_iam_role.lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/ticketstoheaven/*"
      }
    ]
  })
}

# IAM Role for API Gateway CloudWatch Logs
resource "aws_iam_role" "api_gateway_cloudwatch_role" {
  name               = local.api_gateway_role_name
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# IAM Policy for API Gateway to write CloudWatch Logs
resource "aws_iam_role_policy" "api_gateway_cloudwatch" {
  name   = "${local.api_gateway_role_name}-cloudwatch"
  role   = aws_iam_role.api_gateway_cloudwatch_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/apigateway/*"
      }
    ]
  })
}
