# Stripe API Key Secret
resource "aws_secretsmanager_secret" "stripe_api_key" {
  name                    = var.stripe_api_key_secret_name
  description             = "Stripe API secret key for TicketsToHeaven"
  recovery_window_in_days = 7

  tags = merge(
    local.common_tags,
    {
      Name        = var.stripe_api_key_secret_name
      Description = "Stripe API key"
    }
  )
}

# Placeholder for Stripe API Key Secret Version
# In production, replace with actual secret value using:
# aws secretsmanager put-secret-value --secret-id ticketstoheaven/stripe-api-key --secret-string "YOUR_STRIPE_KEY"
resource "aws_secretsmanager_secret_version" "stripe_api_key_version" {
  secret_id     = aws_secretsmanager_secret.stripe_api_key.id
  secret_string = jsonencode({
    api_key = "sk_live_placeholder_replace_with_actual_key"
  })
}

# Third-Party API Key Secret
resource "aws_secretsmanager_secret" "third_party_api_key" {
  name                    = var.third_party_api_key_secret_name
  description             = "Third-party fulfillment API key for TicketsToHeaven"
  recovery_window_in_days = 7

  tags = merge(
    local.common_tags,
    {
      Name        = var.third_party_api_key_secret_name
      Description = "Third-party API key"
    }
  )
}

# Placeholder for Third-Party API Key Secret Version
# In production, replace with actual secret value using:
# aws secretsmanager put-secret-value --secret-id ticketstoheaven/third-party-api-key --secret-string "YOUR_THIRD_PARTY_KEY"
resource "aws_secretsmanager_secret_version" "third_party_api_key_version" {
  secret_id     = aws_secretsmanager_secret.third_party_api_key.id
  secret_string = jsonencode({
    api_key = "third_party_key_placeholder_replace_with_actual_key"
  })
}

# Parameter Store: Third-Party API Endpoint
resource "aws_ssm_parameter" "third_party_api_endpoint" {
  name        = var.third_party_api_endpoint_param_name
  description = "Third-party fulfillment API endpoint URL"
  type        = "String"
  value       = "https://api.example.com/fulfill"  # Replace with actual endpoint

  tags = merge(
    local.common_tags,
    {
      Name        = "third-party-api-endpoint"
      Description = "Third-party API endpoint URL"
    }
  )
}

# Parameter Store: Feature Flags
resource "aws_ssm_parameter" "feature_flags" {
  name        = "/ticketstoheaven/feature-flags"
  description = "Feature flags for TicketsToHeaven application"
  type        = "String"
  value = jsonencode({
    enable_payment_processing = true
    enable_fulfillment_api    = true
    enable_notifications      = true
  })

  tags = merge(
    local.common_tags,
    {
      Name        = "feature-flags"
      Description = "Application feature flags"
    }
  )
}

# Parameter Store: Application Configuration
resource "aws_ssm_parameter" "app_config" {
  name        = "/ticketstoheaven/app-config"
  description = "General application configuration"
  type        = "String"
  value = jsonencode({
    max_order_timeout_seconds = 300
    payment_retry_attempts    = 3
    fulfillment_retry_attempts = 5
  })

  tags = merge(
    local.common_tags,
    {
      Name        = "app-config"
      Description = "Application configuration"
    }
  )
}
