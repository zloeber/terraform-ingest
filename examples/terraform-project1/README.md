# TicketsToHeaven - Terraform Infrastructure

This Terraform configuration provisions a serverless infrastructure for the TicketsToHeaven order management and payment processing platform on AWS.

## Architecture Overview

The infrastructure consists of the following components:

```
┌─────────────────────────────────────────────────────────────┐
│                         Users                                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
          ┌──────────────────────────────┐
          │   CloudFront Distribution    │ (CDN & Caching)
          └──────────────┬───────────────┘
                         │
         ┌───────────────┴────────────────┐
         │                                │
         ▼                                ▼
    ┌─────────┐              ┌──────────────────────┐
    │    S3   │              │   API Gateway        │
    │ Website │              │   + Lambda           │
    │ Assets  │              │                      │
    └─────────┘              └────────┬─────────────┘
                                      │
                  ┌───────────────────┼───────────────────┐
                  │                   │                   │
                  ▼                   ▼                   ▼
          ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
          │   DynamoDB   │   │   DynamoDB   │   │   DynamoDB   │
          │   Orders     │   │  Customers   │   │   Payments   │
          └──────────────┘   └──────────────┘   └──────────────┘
                  │
          ┌───────┴────────┐
          │                │
          ▼                ▼
    ┌──────────────┐  ┌──────────────────┐
    │    Stripe    │  │  Third-Party API │
    │   Webhooks   │  │  Fulfillment     │
    └──────────────┘  └──────────────────┘
```

## Key Components

### Frontend (S3 + CloudFront)
- **S3 Bucket**: Stores Vite + TypeScript compiled assets (HTML, CSS, JS)
- **CloudFront**: Global CDN for low-latency content delivery
- **Origin Access Control**: Secures S3 bucket to only allow CloudFront access
- **Caching**: Optimized cache policies for HTML (60s TTL) and static assets (1hr TTL)

### Backend API (API Gateway + Lambda)
- **REST API Endpoints**:
  - `POST /orders` - Create new orders (order processing Lambda)
  - `POST /webhooks/stripe` - Handle Stripe payment webhooks (webhook handler Lambda)
- **Request Validation**: JSON schema validation for order payloads
- **Logging**: CloudWatch Logs integration for debugging and monitoring
- **CORS**: Configured for cross-origin requests from frontend

### Database (DynamoDB)
- **Orders Table**: Stores order information with customer and status GSIs
- **Customers Table**: Stores customer profiles with email GSI
- **Payments Table**: Stores payment transactions with order and status GSIs
- **Features**: Point-in-time recovery, on-demand billing, server-side encryption

### Security & Configuration
- **Secrets Manager**: Stripe API key and third-party API credentials
- **Parameter Store**: Non-sensitive config like API endpoints and feature flags
- **IAM Roles**: Fine-grained least-privilege access policies
- **Lambda Execution Role**: Permissions for DynamoDB, Secrets Manager, Parameter Store, and CloudWatch

### Monitoring
- **CloudWatch Logs**: Centralized logging for Lambda, API Gateway, and DynamoDB
- **CloudWatch Alarms**: Error tracking, throttling alerts, and performance metrics
- **Log Groups**: Organized by service with 7-day retention (configurable)

## Prerequisites

1. **AWS Account**: Active AWS account with appropriate permissions
2. **Terraform**: Version 1.0 or later
3. **AWS CLI**: Configured with credentials (`aws configure`)
4. **Git**: For version control (optional but recommended)

## Project Structure

```
terraform/
├── providers.tf              # AWS provider configuration
├── variables.tf              # Input variables
├── locals.tf                 # Local values and data sources
├── s3_cloudfront.tf          # S3 bucket and CloudFront distribution
├── dynamodb.tf               # DynamoDB tables
├── lambda.tf                 # Lambda functions
├── api_gateway.tf            # API Gateway configuration
├── iam.tf                    # IAM roles and policies
├── secrets.tf                # Secrets Manager and Parameter Store
├── cloudwatch.tf             # CloudWatch logs and alarms
├── outputs.tf                # Output values
├── terraform.tfvars.example  # Example variables file
├── lambda_placeholder.js     # Placeholder Lambda code
└── README.md                 # This file
```

## Quick Start

### 1. Initialize Terraform

```bash
cd terraform
terraform init
```

### 2. Configure Variables

Copy the example variables file and update with your values:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
- Update `domain_name` with your actual domain
- Adjust Lambda memory and timeout if needed
- Add custom tags as required

### 3. Review the Plan

```bash
terraform plan -out=tfplan
```

Review the planned resources carefully before applying.

### 4. Apply Configuration

```bash
terraform apply tfplan
```

This will create all AWS resources. The process typically takes 5-10 minutes.

### 5. Output Configuration

After successful deployment, retrieve important values:

```bash
terraform output cloudfront_distribution_domain_name
terraform output api_gateway_invoke_url
terraform output s3_website_bucket_name
```

## Deployment Instructions

### Upload Frontend Assets

After your Vite + TypeScript build is complete:

```bash
# Build your Vite project
npm run build

# Sync built files to S3
aws s3 sync dist/ s3://$(terraform output -raw s3_website_bucket_name)/ --delete
```

### Configure Lambda Functions

Replace the placeholder Lambda functions with your actual application code:

1. **Order Processing Lambda** (`order_processing`):
   - Handle order creation
   - Validate order data
   - Call fulfillment API
   - Update DynamoDB tables

2. **Webhook Handler Lambda** (`webhook_handler`):
   - Handle Stripe webhook events
   - Update payment status
   - Trigger fulfillment for successful payments

Deploy new Lambda code:

```bash
# Zip your Lambda code
zip lambda-function.zip index.js node_modules/

# Update Lambda function
aws lambda update-function-code \
  --function-name ticketstoheaven-prod-order-processing \
  --zip-file fileb://lambda-function.zip

aws lambda update-function-code \
  --function-name ticketstoheaven-prod-webhook-handler \
  --zip-file fileb://lambda-function.zip
```

### Configure Secrets

Set your actual API keys in Secrets Manager:

```bash
# Stripe API Key
aws secretsmanager put-secret-value \
  --secret-id ticketstoheaven/stripe-api-key \
  --secret-string '{"api_key":"sk_live_YOUR_ACTUAL_KEY"}'

# Third-party Fulfillment API Key
aws secretsmanager put-secret-value \
  --secret-id ticketstoheaven/third-party-api-key \
  --secret-string '{"api_key":"your_actual_api_key"}'
```

Update the third-party API endpoint:

```bash
aws ssm put-parameter \
  --name /ticketstoheaven/third-party-api-endpoint \
  --value "https://api.fulfillment-provider.com/v1/orders" \
  --overwrite
```

### Configure DNS

Create a CNAME record in your DNS provider pointing to CloudFront:

```
www.ticketstoheaven.com CNAME d123456789.cloudfront.net
```

## Monitoring & Troubleshooting

### CloudWatch Logs

View Lambda logs:

```bash
aws logs tail /aws/lambda/ticketstoheaven-prod-order-processing --follow
aws logs tail /aws/lambda/ticketstoheaven-prod-webhook-handler --follow
```

View API Gateway logs:

```bash
aws logs tail /aws/apigateway/ticketstoheaven-prod --follow
```

### CloudWatch Metrics

Monitor key metrics:

```bash
# Lambda invocations and errors
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=ticketstoheaven-prod-order-processing \
  --start-time 2024-10-20T00:00:00Z \
  --end-time 2024-10-25T00:00:00Z \
  --period 3600 \
  --statistics Sum

# DynamoDB consumed capacity
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedWriteCapacityUnits \
  --dimensions Name=TableName,Value=ticketstoheaven-prod-orders \
  --start-time 2024-10-20T00:00:00Z \
  --end-time 2024-10-25T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

### Common Issues

**Lambda timeout during order processing:**
- Increase `lambda_timeout` variable
- Check CloudWatch logs for slow API calls
- Verify network connectivity to third-party APIs

**DynamoDB throttling:**
- Monitor `WriteThrottleEvents` and `ReadThrottleEvents` metrics
- Consider enabling DynamoDB streams for asynchronous processing
- Review and optimize query patterns

**CloudFront caching issues:**
- Invalidate cache: `aws cloudfront create-invalidation --distribution-id <ID> --paths "/*"`
- Check CloudFront cache statistics in CloudWatch
- Verify origin headers and cache policies

## Maintenance

### Scaling

Adjust scaling parameters:

```bash
# Increase Lambda memory and timeout
terraform apply -var="lambda_memory_size=1024" -var="lambda_timeout=60"

# Adjust DynamoDB capacity (if using PROVISIONED billing)
# Note: Current config uses PAY_PER_REQUEST (serverless)
```

### Backups

DynamoDB point-in-time recovery (PITR) is enabled. Recover data:

```bash
aws dynamodb restore-table-to-point-in-time \
  --source-table-name ticketstoheaven-prod-orders \
  --target-table-name ticketstoheaven-prod-orders-restored \
  --use-latest-restorable-time
```

### Updates

Update Terraform configuration and apply:

```bash
terraform plan
terraform apply
```

## Cost Optimization

1. **S3 + CloudFront**: Pay per GB transferred + CloudFront requests
2. **Lambda**: Pay per 1M invocations ($0.20) + GB-seconds
3. **DynamoDB**: Pay per million read/write units (on-demand mode)
4. **API Gateway**: Pay per million requests ($3.50)
5. **CloudWatch**: Pay for logs ingestion and storage

**Optimization tips:**
- Use CloudFront aggressive caching for static assets
- Implement Lambda code optimization for faster execution
- Monitor DynamoDB usage with CloudWatch metrics
- Set log retention to reduce storage costs
- Use API Gateway throttling to prevent runaway costs

## Security Best Practices

1. **Secrets Management**:
   - Rotate API keys regularly
   - Use KMS encryption for secrets
   - Limit IAM permissions for Secrets Manager access

2. **Network**:
   - Use CloudFront for HTTPS/TLS encryption
   - Enable HTTPS-only for all endpoints
   - Restrict API Gateway access with resource policies

3. **Access Control**:
   - Use least-privilege IAM policies
   - Enable CloudTrail for audit logging
   - Use AWS KMS for encryption keys

4. **Monitoring**:
   - Enable CloudWatch alarms for errors
   - Monitor unusual Lambda execution patterns
   - Set up alerts for failed webhook processing

## Disaster Recovery

### State File Backup

Protect your Terraform state:

```bash
# Enable remote state (S3 + DynamoDB)
# Uncomment the backend configuration in providers.tf
# Create S3 bucket and DynamoDB table for state
# Then run: terraform init
```

### Infrastructure Recovery

Recover from accidental deletion:

```bash
# List resources in state
terraform state list

# Manually import resources if needed
terraform import <resource_type>.<resource_name> <aws_resource_id>
```

### Data Recovery

Use DynamoDB PITR:

```bash
# List restore points (up to 35 days)
aws dynamodb list-backups --table-name ticketstoheaven-prod-orders
```

## Cleanup

To destroy all resources (caution - this deletes all data):

```bash
terraform destroy
```

You'll be prompted to confirm before destruction. Estimated cleanup time: 5-10 minutes.

## Support & Documentation

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [API Gateway Documentation](https://docs.aws.amazon.com/apigateway/)
- [DynamoDB Documentation](https://docs.aws.amazon.com/dynamodb/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [CloudPosse Terraform Modules](https://github.com/cloudposse)

## License

This Terraform configuration is provided as-is for the TicketsToHeaven project.

---

**Last Updated**: October 25, 2025  
**Terraform Version**: >= 1.0  
**AWS Provider Version**: ~> 5.0  
**Project**: TicketsToHeaven  
**Environment**: Production
