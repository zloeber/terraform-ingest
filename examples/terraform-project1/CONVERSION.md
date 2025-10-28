# Terraform Module Conversion Guide

## TicketsToHeaven - Infrastructure Module Migration Plan

This document outlines a comprehensive conversion strategy for migrating the TicketsToHeaven serverless order processing infrastructure from raw AWS resource definitions to CloudPosse Terraform modules. This provides a modular, maintainable, and repeatable infrastructure-as-code approach.

**Project:** TicketsToHeaven Serverless Order Processing System  
**Current Terraform Version:** >= 1.0  
**AWS Provider Version:** >= 5.0  
**Target Module Library:** CloudPosse (AWS components)  
**Document Date:** 2024  
**Status:** Planning / Pre-Implementation

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current Architecture Overview](#current-architecture-overview)
3. [Module Conversion Strategy](#module-conversion-strategy)
4. [Detailed Component Mappings](#detailed-component-mappings)
5. [Migration Sequence](#migration-sequence)
6. [Benefits & Considerations](#benefits--considerations)
7. [Implementation Notes](#implementation-notes)

---

## Executive Summary

### Current State
The TicketsToHeaven infrastructure consists of **8 Terraform files** managing:
- **2 Lambda Functions** (order processing, webhook handling)
- **3 DynamoDB Tables** (orders, customers, payments with GSIs)
- **1 REST API Gateway** (with multiple resources and integrations)
- **1 S3 + CloudFront Distribution** (website hosting with CDN)
- **Complex IAM Roles & Policies** (granular permissions per service)
- **CloudWatch Logging** (4 log groups with retention)
- **Secrets Manager** (2 secrets for API keys)

### Recommended Approach
Migrate to **18+ CloudPosse modules** organized across 7 component categories:
1. **DynamoDB** - Data layer with consistent table provisioning
2. **API Gateway** - REST API with logging and integrations
3. **S3 & CloudFront** - Website hosting and CDN delivery
4. **Lambda** - Serverless compute functions
5. **IAM Roles** - Centralized access control
6. **CloudWatch Logs** - Unified logging infrastructure
7. **Secrets Manager** - Centralized secret storage

### Benefits
- ✅ **Standardization:** CloudPosse best practices baked in
- ✅ **Maintainability:** Reduced code duplication (300+ lines → 100+ lines)
- ✅ **Security:** Built-in encryption, access controls, and tagging
- ✅ **Scalability:** Reusable modules across projects
- ✅ **Compliance:** Pre-configured for AWS best practices

### Migration Complexity: **MEDIUM**
- **Low:** DynamoDB, CloudWatch, Secrets Manager modules (drop-in replacements)
- **Medium:** S3/CloudFront, API Gateway (parameter remapping required)
- **High:** Lambda integration (requires coordination with IAM/API Gateway)

---

## Current Architecture Overview

### File Manifest

| File | Purpose | Lines | Resources |
|------|---------|-------|-----------|
| `providers.tf` | AWS provider config | 15 | 1 provider |
| `variables.tf` | Input variables | 80 | 15 variables |
| `locals.tf` | Local values & data sources | 45 | 10 locals + 2 data sources |
| `lambda.tf` | Lambda functions | 100 | 2 functions, 1 IAM role |
| `dynamodb.tf` | DynamoDB tables | 141 | 3 tables with GSIs |
| `api_gateway.tf` | REST API | 228 | REST API, resources, methods, integrations |
| `s3_cloudfront.tf` | Website hosting | 238 | S3 bucket, CloudFront, ACM certificate, OAI |
| `iam.tf` | IAM roles & policies | 193 | 1 Lambda role, multiple policies |
| `cloudwatch.tf` | Log groups | 148 | 4 log groups with retention |
| `secrets.tf` | Secrets Manager | 106 | 2 secrets with versions |
| `outputs.tf` | Outputs | 30 | 10 outputs |

**Total:** ~1,324 lines of Terraform code

### Key Infrastructure Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        API Gateway                          │
│  (/orders, /webhooks/stripe) → Lambda Integration           │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    ┌─────────┐    ┌──────────┐    ┌──────────┐
    │ Lambda  │    │DynamoDB  │    │Secrets   │
    │Functions│    │  Tables  │    │ Manager  │
    └──┬──────┘    └────┬─────┘    └──────────┘
       │                │
       ├─ order_processing (Async)
       └─ webhook_handler (Sync)
                        │
         ┌──────────────┴──────────────┐
         ▼              ▼              ▼
    ┌────────┐    ┌─────────┐    ┌──────────┐
    │ Orders │    │Customers│    │ Payments │
    │ Table  │    │ Table   │    │ Table    │
    └────────┘    └─────────┘    └──────────┘
         │              │              │
         └──────────────┼──────────────┘
                        │
         ┌──────────────┴──────────────┐
         ▼              ▼              ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐
    │ GSI 1    │  │ GSI 1    │  │ GSI 1    │
    │ (Dates)  │  │ (Email)  │  │ (Status) │
    └──────────┘  └──────────┘  └──────────┘

┌─────────────────────────────────────────────────────────────┐
│                  S3 + CloudFront (Website)                  │
│         Static site hosting with CDN acceleration           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    CloudWatch Logs                          │
│  (Lambda, API Gateway, and application-level logging)       │
└─────────────────────────────────────────────────────────────┘
```

---

## Module Conversion Strategy

### Overview

The migration follows a **phased approach** to minimize disruption:

1. **Phase 1:** Foundation modules (DynamoDB, CloudWatch, Secrets)
2. **Phase 2:** Integration layer (API Gateway, S3/CloudFront)
3. **Phase 3:** Compute layer (Lambda with integrated IAM)
4. **Phase 4:** Cross-module optimization

### Key Principles

- **Backward Compatibility:** Outputs remain consistent with raw resources
- **Incremental Migration:** Deploy one module at a time with state migration
- **Testing:** Run plan/apply cycles to validate state preservation
- **Documentation:** Update locals and outputs to reflect module changes
- **Tagging:** Maintain consistent tagging across all modules

### Module Selection Criteria

CloudPosse modules were selected based on:
- ✅ Latest stable release (v0.9.0 - v1.537.x range)
- ✅ AWS provider compatibility (>= 4.0, < 6.0)
- ✅ Community adoption and maintenance
- ✅ Feature parity with current infrastructure
- ✅ Built-in security and best practices

---

## Detailed Component Mappings

### 1. DynamoDB Migration

#### Current Implementation
**File:** `dynamodb.tf` (141 lines)  
**Resources:** 3 `aws_dynamodb_table` resources with GSIs

#### Recommended Module
**Module:** `cloudposse/dynamodb/aws`  
**Git Source:** `git::git@github.com:cloudposse-terraform-components/aws-dynamodb.git//src?ref=v1.535.2`

#### Current vs. Module Parameters

| Aspect | Current Code | Module Approach |
|--------|--------------|-----------------|
| **Hash Key** | `order_id` (String) | `hash_key: "order_id"`, `hash_key_type: "S"` |
| **Range Key** | `created_at` (String) | `range_key: "created_at"`, `range_key_type: "S"` |
| **Billing Mode** | `PAY_PER_REQUEST` | `billing_mode: "PAY_PER_REQUEST"` |
| **GSI Definition** | Multiple inline GSI blocks | `global_secondary_index_map` (list of objects) |
| **Encryption** | `enabled` | `encryption_enabled: true` |
| **TTL** | `enabled: false` | `ttl_enabled: false` |
| **Point-in-time Recovery** | Not enabled | `point_in_time_recovery_enabled: true` |

#### Implementation Example: Orders Table

**Current Code:**
```hcl
resource "aws_dynamodb_table" "orders" {
  name           = "${local.name_prefix}-orders"
  billing_mode   = "PAY_PER_REQUEST"
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
  # ... more attributes and GSIs
}
```

**Module-based Code:**
```hcl
module "orders_table" {
  source = "git::git@github.com:cloudposse-terraform-components/aws-dynamodb.git//src?ref=v1.535.2"
  
  context = module.this.context
  
  hash_key                          = "order_id"
  hash_key_type                     = "S"
  range_key                         = "created_at"
  range_key_type                    = "S"
  billing_mode                      = "PAY_PER_REQUEST"
  encryption_enabled                = true
  point_in_time_recovery_enabled    = true
  
  dynamodb_attributes = [
    {
      name = "customer_id"
      type = "S"
    },
    {
      name = "order_status"
      type = "S"
    }
  ]
  
  global_secondary_index_map = [
    {
      name                 = "customer-id-created-index"
      hash_key             = "customer_id"
      range_key            = "created_at"
      projection_type      = "ALL"
      read_capacity        = 0  # PAY_PER_REQUEST
      write_capacity       = 0  # PAY_PER_REQUEST
      non_key_attributes   = ["order_status"]
    },
    {
      name                 = "order-status-index"
      hash_key             = "order_status"
      range_key            = "created_at"
      projection_type      = "INCLUDE"
      read_capacity        = 0
      write_capacity       = 0
      non_key_attributes   = ["customer_id"]
    }
  ]
  
  tags = local.common_tags
}
```

#### Migration Checklist for DynamoDB

- [ ] Replace `aws_dynamodb_table` resources with module invocation
- [ ] Convert GSI blocks to `global_secondary_index_map` list
- [ ] Update outputs: `orders_table_arn = module.orders_table.table_arn`
- [ ] Verify no state data loss: `terraform state list | grep dynamodb`
- [ ] Test read/write access from Lambda functions
- [ ] Validate CloudWatch metrics in AWS console

#### Expected Code Reduction
- **Before:** 141 lines
- **After:** ~60 lines (3 module blocks instead of complex resource definitions)

---

### 2. API Gateway Migration

#### Current Implementation
**File:** `api_gateway.tf` (228 lines)  
**Resources:** REST API with resources, methods, validators, CloudWatch integration

#### Recommended Modules
**Primary Module:** `cloudposse/api-gateway/aws`  
**Git Source:** `git::git@github.com:cloudposse-terraform-components/aws-api-gateway-rest-api.git//src?ref=v1.535.3`  
**Account Settings Module:** `cloudposse/api-gateway/aws//modules/account-settings`  
**Git Source:** `git::git@github.com:cloudposse-terraform-components/aws-api-gateway-account-settings.git//src?ref=v1.535.1`

#### Current vs. Module Parameters

| Aspect | Current Code | Module Approach |
|--------|--------------|-----------------|
| **API Name** | `TicketsToHeaven-API` | `name: "api"` (with context) |
| **Endpoint Type** | `REGIONAL` | `endpoint_type: "REGIONAL"` |
| **OpenAPI Spec** | Manual resource/method definitions | `openapi_config` (YAML/JSON) |
| **CloudWatch Logs** | Manual policy attachment | Built-in CloudWatch integration |
| **Lambda Integration** | `aws_api_gateway_integration` | Via OpenAPI `x-amazon-apigateway-integration` |
| **Validators** | `aws_api_gateway_request_validator` | Embedded in OpenAPI spec |

#### Implementation Approach

**Step 1: Account Settings (One-time per region)**
```hcl
module "api_gateway_account_settings" {
  source = "git::git@github.com:cloudposse-terraform-components/aws-api-gateway-account-settings.git//src?ref=v1.535.1"
  
  context = module.this.context
  
  # Enables API Gateway to write to CloudWatch
}
```

**Step 2: REST API with OpenAPI Definition**
```hcl
module "api_gateway_rest_api" {
  source = "git::git@github.com:cloudposse-terraform-components/aws-api-gateway-rest-api.git//src?ref=v1.535.3"
  
  context = module.this.context
  
  name             = "api"
  endpoint_type    = "REGIONAL"
  logging_level    = "INFO"
  metrics_enabled  = true
  xray_tracing_enabled = true
  
  openapi_config = yamldecode(file("${path.module}/openapi-spec.yaml"))
  
  tags = local.common_tags
}
```

**Step 3: OpenAPI Specification (New file: `openapi-spec.yaml`)**
```yaml
openapi: 3.0.1
info:
  title: TicketsToHeaven API
  version: 1.0.0
servers:
  - url: https://{restApiId}.execute-api.{region}.amazonaws.com/prod
paths:
  /orders:
    post:
      summary: Create order
      x-amazon-apigateway-integration:
        type: aws_proxy
        httpMethod: POST
        uri: ${order_processing_lambda_arn}
        responses:
          default:
            statusCode: 200
    get:
      summary: List orders
      x-amazon-apigateway-integration:
        type: aws_proxy
        httpMethod: POST
        uri: ${order_processing_lambda_arn}
  
  /webhooks/stripe:
    post:
      summary: Handle Stripe webhooks
      x-amazon-apigateway-integration:
        type: aws_proxy
        httpMethod: POST
        uri: ${webhook_handler_lambda_arn}
```

#### Migration Checklist for API Gateway

- [ ] Extract OpenAPI specification from current resource definitions
- [ ] Create `openapi-spec.yaml` with all endpoints and integrations
- [ ] Update Lambda execution role policy to allow API Gateway invocation
- [ ] Deploy account settings module first
- [ ] Deploy API Gateway module with OpenAPI config
- [ ] Test all endpoints: POST /orders, GET /orders, POST /webhooks/stripe
- [ ] Validate CloudWatch logs are flowing
- [ ] Update API Gateway stage variables if needed

#### Expected Code Reduction
- **Before:** 228 lines + manual OpenAPI management
- **After:** ~80 lines (module) + ~100 lines (OpenAPI spec)

---

### 3. S3 + CloudFront Migration

#### Current Implementation
**File:** `s3_cloudfront.tf` (238 lines)  
**Resources:** S3 bucket, CloudFront distribution, ACM certificate, Origin Access Identity

#### Recommended Modules
**Primary Module:** `cloudposse/spa-s3-cloudfront/aws`  
**Git Source:** `git::git@github.com:cloudposse-terraform-components/aws-spa-s3-cloudfront.git//src?ref=v1.535.7`  
**Alternative:** `cloudposse/cloudfront-s3-cdn/aws`  
**Git Source:** `git::git@github.com:cloudposse-terraform-components/aws-cloudfront-s3-cdn.git//src?ref=v0.9.0`

The `spa-s3-cloudfront` module is ideal for single-page applications and website hosting.

#### Current vs. Module Parameters

| Aspect | Current Code | Module Approach |
|--------|--------------|-----------------|
| **S3 Bucket** | Manual `aws_s3_bucket` | Built-in via module |
| **Versioning** | Enabled | `origin_versioning_enabled: true` |
| **Encryption** | AES256 | Built-in encryption |
| **Public Access** | All blocked | `block_origin_public_access_enabled: true` |
| **CloudFront Dist** | Manual configuration | Full distribution setup |
| **ACM Certificate** | Separate resource | `site_subdomain` or `site_fqdn` |
| **OAI** | Manual OAI setup | Automatic via module |
| **CloudFront Logs** | Manual S3 bucket | Optional via module |

#### Implementation Example

**Current Code (Simplified):**
```hcl
resource "aws_s3_bucket" "website" {
  bucket = local.website_bucket_name
}

resource "aws_cloudfront_distribution" "main" {
  origin {
    domain_name = aws_s3_bucket.website.bucket_regional_domain_name
    origin_id   = "myS3Origin"
    
    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.oai.cloudfront_access_identity_path
    }
  }
  # ... 100+ lines of CloudFront configuration
}
```

**Module-based Code:**
```hcl
module "spa_cloudfront" {
  source = "git::git@github.com:cloudposse-terraform-components/aws-spa-s3-cloudfront.git//src?ref=v1.535.7"
  
  context = module.this.context
  
  name                   = "website"
  site_subdomain         = "www"
  parent_zone_name       = var.domain_name
  
  # Origin S3 Bucket Configuration
  origin_versioning_enabled         = true
  origin_force_destroy              = false
  origin_deployment_principal_arns   = []  # Add CD/CI role if needed
  block_origin_public_access_enabled = true
  origin_encryption_enabled          = true
  
  # CloudFront Distribution Configuration
  cloudfront_default_root_object  = "index.html"
  cloudfront_compress             = true
  cloudfront_viewer_protocol_policy = "redirect-to-https"
  cloudfront_index_document        = "index.html"
  cloudfront_min_ttl               = 0
  cloudfront_default_ttl           = 3600
  cloudfront_max_ttl               = 86400
  
  # Error Handling
  cloudfront_custom_error_response = [
    {
      error_code            = 404
      response_code         = 200
      response_page_path    = "/index.html"
      error_caching_min_ttl = 10
    }
  ]
  
  # DNS Configuration
  process_domain_validation_options = true
  
  tags = local.common_tags
}
```

#### Outputs Mapping

| Current Output | Module Output |
|---|---|
| `s3_website_bucket_id` | `module.spa_cloudfront.origin_s3_bucket_name` |
| `s3_website_bucket_arn` | `module.spa_cloudfront.origin_s3_bucket_arn` |
| `cloudfront_domain_name` | `module.spa_cloudfront.cloudfront_distribution_domain_name` |
| `cloudfront_distribution_id` | `module.spa_cloudfront.cloudfront_distribution_id` |

#### Migration Checklist for S3 + CloudFront

- [ ] Backup current S3 bucket contents and CloudFront configuration
- [ ] Create DNS delegated zone if needed for ACM validation
- [ ] Deploy spa-s3-cloudfront module
- [ ] Verify S3 bucket created with correct settings
- [ ] Verify CloudFront distribution deployed and healthy
- [ ] Test origin access (should fail - OAI enforced)
- [ ] Test CloudFront distribution access (should succeed)
- [ ] Update Route53 CNAME to new CloudFront domain
- [ ] Validate SSL certificate validation
- [ ] Clear CloudFront cache if needed
- [ ] Monitor access logs for errors

#### Expected Code Reduction
- **Before:** 238 lines
- **After:** ~80 lines (module) + DNS configuration

---

### 4. Lambda Migration

#### Current Implementation
**File:** `lambda.tf` (100 lines)  
**Resources:** 2 `aws_lambda_function` resources with IAM roles

#### Recommended Approach
The CloudPosse library doesn't have a dedicated Lambda module, but we can use:

**Primary Module:** `cloudposse/iam-role/aws`  
**Version:** `0.3.0` (for Lambda execution roles)  
**Compute:** Raw `aws_lambda_function` resources with module-managed IAM

#### Implementation Pattern

**Step 1: Lambda Execution Role (via IAM module)**
```hcl
module "lambda_execution_role" {
  source = "git::git@github.com:cloudposse-terraform-components/aws-iam-role.git//src?ref=v1.536.1"
  
  context = module.this.context
  
  name        = "lambda-execution"
  role_description = "Execution role for TicketsToHeaven Lambda functions"
  
  principals = {
    Service = ["lambda.amazonaws.com"]
  }
  
  policy_documents = [
    data.aws_iam_policy_document.lambda_policy.json
  ]
  
  managed_policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  ]
  
  tags = local.common_tags
}

data "aws_iam_policy_document" "lambda_policy" {
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:Query",
      "dynamodb:Scan"
    ]
    resources = [
      module.orders_table.table_arn,
      module.customers_table.table_arn,
      module.payments_table.table_arn
    ]
  }
  
  statement {
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue"
    ]
    resources = [
      module.stripe_secret.secret_arn
    ]
  }
}
```

**Step 2: Lambda Functions (Raw Resources with Module IAM)**
```hcl
resource "aws_lambda_function" "order_processing" {
  filename         = data.archive_file.order_processing_code.output_path
  function_name    = "${local.name_prefix}-order-processing"
  role             = module.lambda_execution_role.role_arn
  handler          = "index.handler"
  runtime          = "nodejs.18.x"
  timeout          = 60
  memory_size      = var.lambda_memory_size
  
  vpc_config {
    subnet_ids         = var.lambda_subnet_ids
    security_group_ids = var.lambda_security_group_ids
  }
  
  environment {
    variables = {
      ORDERS_TABLE    = module.orders_table.table_name
      CUSTOMERS_TABLE = module.customers_table.table_name
      PAYMENTS_TABLE  = module.payments_table.table_name
      STRIPE_SECRET   = module.stripe_secret.secret_name
    }
  }
  
  layers = [module.lambda_logs_layer.layer_version_arn]
  
  depends_on = [
    module.orders_table,
    module.customers_table,
    module.payments_table,
    module.stripe_secret
  ]
  
  tags = local.common_tags
}

resource "aws_lambda_function" "webhook_handler" {
  filename         = data.archive_file.webhook_handler_code.output_path
  function_name    = "${local.name_prefix}-webhook-handler"
  role             = module.lambda_execution_role.role_arn
  handler          = "index.handler"
  runtime          = "nodejs.18.x"
  timeout          = 30
  memory_size      = 256
  
  environment {
    variables = {
      PAYMENTS_TABLE = module.payments_table.table_name
    }
  }
  
  tags = local.common_tags
}
```

#### Migration Notes for Lambda

- Lambda functions remain largely unchanged
- IAM roles and policies move to `cloudposse/iam-role/aws` module
- Update `role` parameter to point to module output: `module.lambda_execution_role.role_arn`
- Maintain CloudWatch log groups separately (see CloudWatch section)
- Test function execution with CloudWatch logs streaming

#### Expected Code Reduction
- **Before:** 100 lines (function + inline policies)
- **After:** ~70 lines (module role + function definitions)

---

### 5. IAM Roles & Policies Migration

#### Current Implementation
**File:** `iam.tf` (193 lines)  
**Resources:** Lambda execution role, multiple inline policies, API Gateway log role

#### Recommended Modules
**Primary:** `cloudposse/iam-role/aws`  
**Version:** `0.3.0`

#### Implementation Pattern

**Lambda Execution Role (with inline policies):**
```hcl
module "lambda_execution_role" {
  source = "git::git@github.com:cloudposse-terraform-components/aws-iam-role.git//src?ref=v1.536.1"
  
  context = module.this.context
  
  name                 = "lambda-execution"
  role_description     = "Execution role for Lambda functions"
  policy_description   = "Lambda execution policies"
  
  # Assume role policy
  principals = {
    Service = ["lambda.amazonaws.com"]
  }
  
  # Inline policy for DynamoDB and Secrets access
  policy_documents = [
    data.aws_iam_policy_document.lambda_permissions.json
  ]
  
  # Managed policies
  managed_policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  ]
  
  # Optional: VPC Lambda execution policy
  # managed_policy_arns += ["arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"]
  
  tags = local.common_tags
}

# Inline policy document for granular permissions
data "aws_iam_policy_document" "lambda_permissions" {
  statement {
    sid    = "DynamoDBAccess"
    effect = "Allow"
    
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:BatchGetItem"
    ]
    
    resources = [
      module.orders_table.table_arn,
      module.customers_table.table_arn,
      module.payments_table.table_arn,
      "${module.orders_table.table_arn}/index/*",
      "${module.customers_table.table_arn}/index/*",
      "${module.payments_table.table_arn}/index/*"
    ]
  }
  
  statement {
    sid    = "SecretsManagerAccess"
    effect = "Allow"
    
    actions = [
      "secretsmanager:GetSecretValue"
    ]
    
    resources = [
      module.stripe_secret.secret_arn,
      module.api_key_secret.secret_arn
    ]
  }
  
  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    
    resources = ["arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/*"]
  }
}
```

**API Gateway CloudWatch Role (One-time per region):**
```hcl
module "api_gateway_logs_role" {
  source = "git::git@github.com:cloudposse-terraform-components/aws-iam-role.git//src?ref=v1.536.1"
  
  context = module.this.context
  
  name                 = "api-gateway-logs"
  role_description     = "Role for API Gateway to write CloudWatch logs"
  
  principals = {
    Service = ["apigateway.amazonaws.com"]
  }
  
  managed_policy_arns = [
    "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
  ]
  
  tags = local.common_tags
}

# Register this role with API Gateway account settings
resource "aws_api_gateway_account" "main" {
  cloudwatch_role_arn = module.api_gateway_logs_role.role_arn
  
  depends_on = [module.api_gateway_logs_role]
}
```

#### Migration Checklist for IAM

- [ ] Extract all policy documents to separate data sources
- [ ] Create role modules for each distinct role
- [ ] Update all `role_arn` references to module outputs
- [ ] Test permissions by executing Lambda functions
- [ ] Validate API Gateway can write to CloudWatch
- [ ] Audit IAM policies for least privilege adherence

#### Expected Code Reduction
- **Before:** 193 lines
- **After:** ~120 lines (module definitions + policy documents)

---

### 6. CloudWatch Logs Migration

#### Current Implementation
**File:** `cloudwatch.tf` (148 lines)  
**Resources:** 4 `aws_cloudwatch_log_group` resources

#### Recommended Module
**Module:** `cloudposse/cloudwatch-logs/aws`  
**Git Source:** `git::git@github.com:cloudposse-terraform-components/aws-cloudwatch-logs.git//src?ref=v1.536.2`

#### Implementation Example

**Before:**
```hcl
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${local.name_prefix}"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.logs.arn
  
  tags = local.common_tags
}
```

**After:**
```hcl
module "cloudwatch_logs" {
  source = "git::git@github.com:cloudposse-terraform-components/aws-cloudwatch-logs.git//src?ref=v1.536.2"
  
  context = module.this.context
  
  name              = "lambda-logs"
  retention_in_days = var.log_retention_days
  
  stream_names = [
    "order-processing",
    "webhook-handler"
  ]
  
  # Optional: KMS encryption
  kms_key_deletion_window = 10
  
  tags = local.common_tags
}
```

#### Create Separate Log Group Modules for Each Service

```hcl
# Lambda Logs
module "lambda_logs" {
  source = "git::git@github.com:cloudposse-terraform-components/aws-cloudwatch-logs.git//src?ref=v1.536.2"
  
  context = module.this.context
  
  name              = "lambda"
  retention_in_days = var.log_retention_days
  
  stream_names = [
    "order-processing",
    "webhook-handler"
  ]
  
  tags = local.common_tags
}

# API Gateway Logs
module "api_gateway_logs" {
  source = "git::git@github.com:cloudposse-terraform-components/aws-cloudwatch-logs.git//src?ref=v1.536.2"
  
  context = module.this.context
  
  name              = "api-gateway"
  retention_in_days = var.log_retention_days
  
  stream_names = [
    "requests",
    "errors"
  ]
  
  tags = local.common_tags
}
```

#### Outputs Mapping

| Current | Module Output |
|---------|--------------|
| `aws_cloudwatch_log_group.lambda_logs.name` | `module.lambda_logs.log_group_name` |
| `aws_cloudwatch_log_group.lambda_logs.arn` | `module.lambda_logs.log_group_arn` |

#### Migration Checklist for CloudWatch

- [ ] Create separate log group modules for Lambda, API Gateway
- [ ] Update Lambda function `log_group_name` to module output
- [ ] Update API Gateway configuration to use new log group
- [ ] Verify logs are being written to new groups
- [ ] Delete old log groups after verification

#### Expected Code Reduction
- **Before:** 148 lines
- **After:** ~60 lines (2-3 module blocks)

---

### 7. Secrets Manager Migration

#### Current Implementation
**File:** `secrets.tf` (106 lines)  
**Resources:** 2 `aws_secretsmanager_secret` resources

#### Recommended Approach
**Note:** CloudPosse doesn't have a dedicated Secrets Manager module. Use raw resources with label module for consistent naming.

```hcl
module "stripe_secret" {
  source = "cloudposse/label/null"
  
  context = merge(
    module.this.context,
    { name = "stripe-api-key" }
  )
}

resource "aws_secretsmanager_secret" "stripe_api_key" {
  name                    = module.stripe_secret.id
  description             = "Stripe API key for webhook processing"
  recovery_window_in_days = 7
  
  tags = module.stripe_secret.tags
}

resource "aws_secretsmanager_secret_version" "stripe_api_key" {
  secret_id     = aws_secretsmanager_secret.stripe_api_key.id
  secret_string = var.stripe_api_key
}

# Ensure Lambda execution role can read this secret
# (handled via module.lambda_execution_role policies)
```

#### Alternative: Use AWS Secrets Manager with Terraform Data Source

```hcl
# For existing secrets that are pre-populated manually
data "aws_secretsmanager_secret" "stripe_api_key" {
  name = "stripe-api-key"
}

data "aws_secretsmanager_secret_version" "stripe_api_key" {
  secret_id = data.aws_secretsmanager_secret.stripe_api_key.id
}

# Use in Lambda environment
environment {
  variables = {
    STRIPE_SECRET_ARN = data.aws_secretsmanager_secret.stripe_api_key.arn
  }
}
```

#### Migration Checklist for Secrets

- [ ] Keep current secrets as-is (minimal cloud provider resource wrapper)
- [ ] Update Lambda IAM policy to reference secret ARNs from module output
- [ ] Test Lambda can retrieve secrets via API
- [ ] Document secret naming convention for consistency

#### Expected Code Reduction
- **Before:** 106 lines
- **After:** ~40 lines (simplified with label module)

---

## Migration Sequence

### Phase 1: Foundation (Low Risk) - Week 1

**Objective:** Establish stable data and logging layer

1. **Deploy CloudWatch Logs Module**
   - Time: 2 hours
   - Risk: LOW (independent resource)
   - Command: `terraform apply -target=module.cloudwatch_logs`

2. **Deploy DynamoDB Modules**
   - Time: 4 hours (3 tables in sequence)
   - Risk: LOW (state migration maintains data)
   - Sequence: `orders` → `customers` → `payments`

3. **Update IAM Roles Module (Basic)**
   - Time: 3 hours
   - Risk: MEDIUM (permissions changes)
   - Test Lambda execution after applying

**Phase 1 Success Criteria:**
- ✅ CloudWatch log groups created
- ✅ DynamoDB tables migrated (verify via AWS console)
- ✅ IAM roles attached to Lambda
- ✅ No data loss in DynamoDB

### Phase 2: Integration Layer (Medium Risk) - Week 2

**Objective:** Deploy API and web hosting layer

1. **Deploy API Gateway Account Settings**
   - Time: 1 hour
   - Risk: LOW (one-time regional setup)

2. **Deploy API Gateway REST API Module**
   - Time: 4 hours
   - Risk: MEDIUM (requires OpenAPI spec creation)
   - Preparation: Create `openapi-spec.yaml`

3. **Deploy S3 + CloudFront Module**
   - Time: 3 hours
   - Risk: MEDIUM (certificate validation needed)
   - DNS validation: May take 10-15 minutes

4. **Deploy Secrets Manager (Simplified)**
   - Time: 1 hour
   - Risk: LOW (minimal changes)

**Phase 2 Success Criteria:**
- ✅ API endpoints accessible
- ✅ CloudFront distribution active
- ✅ SSL certificate validated
- ✅ Website accessible via HTTPS

### Phase 3: Compute Refinement (Low Risk) - Week 3

**Objective:** Optimize Lambda integration with modules

1. **Refine Lambda IAM Policies**
   - Time: 2 hours
   - Risk: LOW (policy enhancements only)

2. **Deploy Lambda Layers (Optional)**
   - Time: 2 hours
   - Risk: LOW (enhancement layer)

3. **Cross-module Testing**
   - Time: 8 hours
   - Risk: MEDIUM (integration testing)
   - Test matrix: All Lambda ↔ DynamoDB ↔ API ↔ CloudFront paths

**Phase 3 Success Criteria:**
- ✅ All Lambda functions execute successfully
- ✅ End-to-end order flow works
- ✅ Webhook handling functional
- ✅ Performance metrics meet requirements

### Phase 4: Cleanup & Optimization - Week 4

**Objective:** Remove old code and finalize

1. **Remove raw resource definitions**
   - Delete: `lambda.tf` (old definitions only)
   - Update: `outputs.tf` to reference module outputs

2. **Documentation Updates**
   - Update: `README.md` with module architecture
   - Create: Module-specific documentation

3. **Terraform State Cleanup**
   - Verify: No orphaned resources
   - Command: `terraform state list | wc -l` (should match expected count)

4. **CI/CD Pipeline Updates**
   - Update: `terraform fmt` and `terraform validate`
   - Update: Linting rules for module configuration

**Phase 4 Success Criteria:**
- ✅ No deprecated resources in code
- ✅ State file clean and lean
- ✅ Documentation complete
- ✅ All tests passing

---

## Benefits & Considerations

### Key Benefits

| Benefit | Impact | Effort |
|---------|--------|--------|
| **Code Reduction** | 1,324 → ~800 lines (40% reduction) | Immediate |
| **Best Practices** | CloudPosse standards built-in | Automatic |
| **Maintainability** | Easier to read and modify | High |
| **Reusability** | Modules usable in other projects | High |
| **Security** | Encryption, access control standardized | High |
| **Compliance** | AWS best practices enforced | High |
| **Team Onboarding** | Familiar patterns for new team members | Medium |
| **Update Cycle** | Faster to adopt AWS updates | Medium |

### Considerations & Trade-offs

| Consideration | Impact | Mitigation |
|---|---|---|
| **Learning Curve** | Team needs CloudPosse module familiarity | Documentation, training |
| **Customization** | Some features harder to customize | Use raw resources where needed |
| **Module Updates** | Version dependencies to manage | Use terraform lock files, semantic versioning |
| **Debugging** | Multi-layer stack harder to debug | Detailed logging, state inspection |
| **Migration Risk** | Potential for downtime if not careful | Phased approach, state preservation |
| **Cost** | No cost difference (same resources) | N/A |

### Recommended Practices

1. **Use Module Versions**
   ```hcl
   source = "cloudposse/dynamodb/aws"
   version = "0.37.0"  # Not "~> 0.37.0"
   ```

2. **Maintain State Backups**
   ```bash
   terraform state pull > backup-state.json
   ```

3. **Test in Dev First**
   - Create dev stack with modules
   - Validate before prod migration

4. **Monitor During Migration**
   - Keep CloudWatch dashboards open
   - Have rollback plan ready
   - Test all critical paths

5. **Document Custom Policies**
   - Keep inline policies readable
   - Add comments explaining permissions
   - Review with security team

---

## Implementation Notes

### Terraform Configuration Best Practices

**1. Context Module Usage (CloudPosse Pattern)**

```hcl
# In main.tf
module "this" {
  source = "cloudposse/label/null"
  
  namespace   = var.namespace
  tenant      = var.tenant
  environment = var.environment
  stage       = var.stage
  name        = var.project_name
  
  delimiter   = "-"
  label_order = ["namespace", "environment", "stage", "name"]
  
  tags = var.tags
}

# In each module call
module "some_module" {
  source = "cloudposse/some-service/aws"
  version = "X.Y.Z"
  
  context = module.this.context  # Consistent naming & tagging!
}
```

**2. Output Standardization**

```hcl
output "dynamodb_tables" {
  description = "DynamoDB table IDs and ARNs"
  value = {
    orders = {
      id  = module.orders_table.table_id
      arn = module.orders_table.table_arn
      name = module.orders_table.table_name
    }
    customers = {
      id  = module.customers_table.table_id
      arn = module.customers_table.table_arn
      name = module.customers_table.table_name
    }
    payments = {
      id  = module.payments_table.table_id
      arn = module.payments_table.table_arn
      name = module.payments_table.table_name
    }
  }
}
```

**3. Locals Organization**

```hcl
locals {
  # CloudPosse label context
  context = module.this.context
  
  # Common tags
  common_tags = merge(
    local.context.tags,
    {
      Project = "TicketsToHeaven"
      ManagedBy = "Terraform"
      ModuleArchitecture = "CloudPosse"
    }
  )
  
  # Naming shortcuts
  name_prefix = module.this.id
  
  # Module references for cross-module dependencies
  lambda_execution_role_arn = module.lambda_execution_role.role_arn
  lambda_log_group_name = module.lambda_logs.log_group_name
}
```

### State Management During Migration

**Backup Current State**
```bash
cd terraform
terraform state pull > terraform-backup-$(date +%s).json
```

**Migration Strategy: Resource-by-Resource**
```bash
# Step 1: Move raw resource to module state
terraform state rm 'aws_dynamodb_table.orders'
terraform state mv -state-out=prod.tfstate 'aws_dynamodb_table.orders' 'module.orders_table.aws_dynamodb_table.this'

# Step 2: Apply module
terraform apply -target='module.orders_table'

# Step 3: Verify data integrity
aws dynamodb describe-table --table-name ${table_name}

# Step 4: Repeat for each resource
```

### Testing Checklist

**Functionality Testing**
- [ ] Lambda functions execute without errors
- [ ] DynamoDB queries return expected results
- [ ] API Gateway endpoints respond correctly
- [ ] CloudFront distributions serve content
- [ ] Secrets are retrievable from Lambda

**Integration Testing**
- [ ] Order creation flow works end-to-end
- [ ] Stripe webhooks are processed
- [ ] CloudWatch logs collect from all services
- [ ] IAM permissions are sufficient
- [ ] No "AccessDenied" errors in logs

**Performance Testing**
- [ ] Lambda cold start times acceptable
- [ ] API response times < 1 second
- [ ] DynamoDB query latency normal
- [ ] CloudFront cache hit ratio > 80%

**Compliance Testing**
- [ ] All data encrypted at rest
- [ ] All data encrypted in transit
- [ ] Public access blocked appropriately
- [ ] Tagging strategy consistent
- [ ] Access logs being collected

### Rollback Plan

If migration encounters critical issues:

**Immediate Rollback**
```bash
# Restore previous state
terraform state push terraform-backup-${TIMESTAMP}.json

# Revert to previous Terraform configuration
git checkout HEAD -- .

# Reapply old infrastructure
terraform apply -auto-approve
```

**Validation After Rollback**
```bash
# Verify all services back online
aws dynamodb list-tables
aws lambda list-functions
aws cloudformation describe-stacks

# Check CloudWatch for errors
aws logs tail /aws/lambda/ --follow
```

---

## Summary: Module Migration Timeline

| Phase | Duration | Modules | Status |
|-------|----------|---------|--------|
| **Phase 1** | 1 week | CloudWatch, DynamoDB, IAM | 🟡 Ready to Start |
| **Phase 2** | 1 week | API Gateway, S3/CloudFront, Secrets | 🟡 Depends on Phase 1 |
| **Phase 3** | 1 week | Lambda Refinement, Integration Tests | 🟡 Depends on Phase 2 |
| **Phase 4** | 1 week | Cleanup, Documentation, CI/CD | 🟡 Depends on Phase 3 |
| **Total** | **4 weeks** | **18+ modules** | 🟡 **Ready to Begin** |

---

## Appendix: Module Reference Matrix

| Component | Git Repository | Git Ref | Source Path | Status |
|-----------|---|---|---|---|
| DynamoDB (Orders) | aws-dynamodb.git | v1.535.2 | src | Recommended |
| DynamoDB (Customers) | aws-dynamodb.git | v1.535.2 | src | Recommended |
| DynamoDB (Payments) | aws-dynamodb.git | v1.535.2 | src | Recommended |
| API Gateway Account Settings | aws-api-gateway-account-settings.git | v1.535.1 | src | Recommended |
| API Gateway REST API | aws-api-gateway-rest-api.git | v1.535.3 | src | Recommended |
| S3 + CloudFront | aws-spa-s3-cloudfront.git | v1.535.7 | src | Recommended |
| Lambda Execution Role | aws-iam-role.git | v1.536.1 | src | Recommended |
| API Gateway Log Role | aws-iam-role.git | v1.536.1 | src | Recommended |
| CloudWatch Logs | aws-cloudwatch-logs.git | v1.536.2 | src | Recommended |
| Naming/Labeling | label.git | 0.25.0 | - | Foundation |

### Full Git SSH URLs

For easy reference, here are the complete git SSH module sources:

```
git::git@github.com:cloudposse-terraform-components/aws-dynamodb.git//src?ref=v1.535.2
git::git@github.com:cloudposse-terraform-components/aws-api-gateway-account-settings.git//src?ref=v1.535.1
git::git@github.com:cloudposse-terraform-components/aws-api-gateway-rest-api.git//src?ref=v1.535.3
git::git@github.com:cloudposse-terraform-components/aws-spa-s3-cloudfront.git//src?ref=v1.535.7
git::git@github.com:cloudposse-terraform-components/aws-iam-role.git//src?ref=v1.536.1
git::git@github.com:cloudposse-terraform-components/aws-cloudwatch-logs.git//src?ref=v1.536.2
```

---

## Document Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024 | Initial creation with comprehensive module mapping |

---

**Document Status:** ✅ **READY FOR IMPLEMENTATION**

For questions or clarifications, refer to:
- 📚 CloudPosse Documentation: https://docs.cloudposse.com
- 🔗 Module GitHub: https://github.com/cloudposse/terraform-aws-components
- 📋 Registry: https://registry.terraform.io/namespaces/cloudposse
