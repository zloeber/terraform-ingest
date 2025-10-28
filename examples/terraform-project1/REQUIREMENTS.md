# TicketsToHeaven - Infrastructure Requirements

## Project Overview
**Project Name:** TicketsToHeaven  
**Purpose:** A Vite + TypeScript website for taking orders, processing payments via Stripe, and calling a third-party fulfillment API  
**AWS Region:** us-east-2  
**Environment:** Production only  
**Created:** October 25, 2025

## Refined Requirements

### Frontend
- **Technology:** Vite + TypeScript
- **Hosting:** AWS CloudFront + S3 (CDN + static asset hosting)
- **Purpose:** Customer-facing order interface

### Backend API
- **Technology:** AWS Lambda (serverless)
- **Functions:**
  - Order processing
  - Stripe payment webhook handling
  - Third-party fulfillment API integration
- **API Gateway:** Required to expose Lambda functions as HTTP endpoints

### Data Storage
- **Primary Database:** DynamoDB (serverless NoSQL)
- **Purpose:** Store order data, customer information, and payment details
- **Scaling:** Automatic on-demand scaling

### Security & Configuration Management
- **AWS Secrets Manager:** Store sensitive credentials
  - Stripe API keys
  - Third-party API keys
  - Database encryption keys
- **AWS Parameter Store:** Store non-sensitive configuration and secure strings

### Logging & Monitoring
- **CloudWatch:** Centralized logging for Lambda, API calls, and system events
- **CloudWatch Metrics:** Monitor Lambda performance, DynamoDB usage, and API latency
- **Log Groups:** Organized by service (Lambda, API Gateway, DynamoDB)

### State Management
- **Type:** Local state (terraform.tfstate)
- **Future Migration:** Can upgrade to S3 + DynamoDB remote backend when ready

## AWS Service Mapping

| Requirement | AWS Service | Notes |
|-------------|-------------|-------|
| Frontend Hosting | CloudFront + S3 | CDN for low-latency content delivery |
| API Backend | Lambda + API Gateway | Serverless, pay-per-request pricing |
| Database | DynamoDB | Serverless NoSQL, auto-scaling |
| Secrets Management | Secrets Manager | Encrypted credential storage |
| Configuration | Parameter Store | Non-sensitive config and secure strings |
| Logging | CloudWatch | Logs, metrics, and alarms |
| IAM Roles | IAM | Least-privilege access for services |

## Key Design Principles
1. **Serverless-First:** Lambda + DynamoDB for minimal operational overhead
2. **Security:** Secrets Manager for all sensitive data, Parameter Store for configuration
3. **Observability:** Comprehensive CloudWatch logging across all components
4. **Scalability:** DynamoDB on-demand billing, Lambda auto-scaling
5. **Cost-Efficiency:** Pay-per-use pricing model for low-traffic scenarios
6. **Best Practices:** Proper tagging, IAM policies, and resource naming conventions

## Terraform Deliverables
- [ ] `providers.tf` - AWS provider configuration
- [ ] `variables.tf` - Input variables and defaults
- [ ] `locals.tf` - Local values for reusable configurations
- [ ] `s3.tf` - S3 bucket for frontend assets
- [ ] `cloudfront.tf` - CloudFront distribution
- [ ] `dynamodb.tf` - DynamoDB tables for orders and related data
- [ ] `lambda.tf` - Lambda function definitions
- [ ] `api_gateway.tf` - API Gateway configuration
- [ ] `iam.tf` - IAM roles and policies
- [ ] `secrets.tf` - Secrets Manager secrets
- [ ] `parameters.tf` - Parameter Store parameters
- [ ] `cloudwatch.tf` - CloudWatch log groups and alarms
- [ ] `outputs.tf` - Output values for deployment reference
- [ ] `README.md` - Deployment instructions
- [ ] `terraform.tfvars` - Variables file (with example)

## Next Steps
1. Research AWS best practices using AWS Documentation
2. Search for existing Terraform modules from terraform-ingest-mcp
3. Design the complete infrastructure in HCL
4. Create production-ready Terraform code
5. Generate deployment documentation
