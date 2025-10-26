# Orders table - stores order information
resource "aws_dynamodb_table" "orders" {
  name           = local.orders_table_name
  billing_mode   = var.dynamodb_billing_mode
  hash_key       = "order_id"
  range_key      = "created_at"

  attribute {
    name = "order_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  attribute {
    name = "customer_id"
    type = "S"
  }

  attribute {
    name = "order_status"
    type = "S"
  }

  # Global Secondary Index for querying by customer_id
  global_secondary_index {
    name            = "customer-id-index"
    hash_key        = "customer_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  # Global Secondary Index for querying by order_status
  global_secondary_index {
    name            = "order-status-index"
    hash_key        = "order_status"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = false
  }

  tags = merge(
    local.common_tags,
    {
      Name        = local.orders_table_name
      Description = "Orders table for TicketsToHeaven"
    }
  )
}

# Customers table - stores customer information
resource "aws_dynamodb_table" "customers" {
  name         = local.customers_table_name
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "customer_id"

  attribute {
    name = "customer_id"
    type = "S"
  }

  attribute {
    name = "email"
    type = "S"
  }

  # Global Secondary Index for querying by email
  global_secondary_index {
    name            = "email-index"
    hash_key        = "email"
    projection_type = "ALL"
  }

  tags = merge(
    local.common_tags,
    {
      Name        = local.customers_table_name
      Description = "Customers table for TicketsToHeaven"
    }
  )
}

# Payments table - stores payment transaction information
resource "aws_dynamodb_table" "payments" {
  name           = local.payments_table_name
  billing_mode   = var.dynamodb_billing_mode
  hash_key       = "payment_id"
  range_key      = "created_at"

  attribute {
    name = "payment_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  attribute {
    name = "order_id"
    type = "S"
  }

  attribute {
    name = "payment_status"
    type = "S"
  }

  # Global Secondary Index for querying by order_id
  global_secondary_index {
    name            = "order-id-index"
    hash_key        = "order_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  # Global Secondary Index for querying by payment_status
  global_secondary_index {
    name            = "payment-status-index"
    hash_key        = "payment_status"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  tags = merge(
    local.common_tags,
    {
      Name        = local.payments_table_name
      Description = "Payments table for TicketsToHeaven"
    }
  )
}
