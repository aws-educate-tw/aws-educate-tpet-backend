
# AWS Lambda Warmer Terraform Module

A Terraform module for deploying an automated Lambda function warming solution. This module helps prevent cold starts in your Lambda functions by periodically invoking them based on tags.

## Overview

This module creates a Lambda function that automatically warms up other Lambda functions based on specified tags. It uses EventBridge Scheduler to trigger the warming process at regular intervals.

## Features

- Tag-based function selection for warming
- Configurable warming schedule
- Separate IAM roles for Lambda and EventBridge Scheduler
- CloudWatch logging for monitoring
- Customizable tag key/value pairs for targeting functions

## Usage

```hcl
module "lambda_warmer" {
  source = "../modules/lambda_warmer"

  aws_region = "ap-northeast-1"
  environment = "production"

  # Optional: Custom configuration
  prewarm_tag_key = "Project"
  prewarm_tag_value = "MyProject"
  lambda_schedule_expression = "rate(5 minutes)"
  scheduler_max_retry_attempts = 0
}
```

### Tagging Lambda Functions for Warming

To mark a Lambda function for warming, add the appropriate tags:

```hcl
resource "aws_lambda_function" "example" {
  # ... other configuration ...

  tags = {
    Prewarm = "true"  # Default tags
    # Or use custom tags as configured in the module
    Project = "MyProject"
  }
}
```

## Requirements

| Name | Version |
|------|---------|
| Terraform | >= 1.8.0 |
| AWS Provider | >= 5.54 |
| Python | >= 3.11 (for Lambda runtime) |

## Variables

### Required Variables

| Name | Description | Type |
|------|-------------|------|
| aws_region | AWS region where the Lambda warmer will be deployed | string |
| environment | Environment name (e.g., prod, dev, staging) | string |

### Optional Variables

| Name | Description | Type | Default |
|------|-------------|------|---------|
| lambda_schedule_expression | Schedule expression for the warmer | string | "rate(5 minutes)" |
| scheduler_max_retry_attempts | Max retry attempts for scheduler | number | 0 |
| prewarm_tag_key | Tag key for identifying functions to warm | string | "Prewarm" |
| prewarm_tag_value | Expected value of the warming tag | string | "true" |

## Outputs

| Name | Description |
|------|-------------|
| scheduler_group_arn | ARN of the EventBridge Scheduler Group |
| scheduler_arn | ARN of the EventBridge Scheduler |
| lambda_function_name | Name of the Lambda warmer function |
| lambda_function_arn | ARN of the Lambda warmer function |
| lambda_role_name | Name of the Lambda IAM Role |
| lambda_role_arn | ARN of the Lambda IAM Role |

## Directory Structure

```plaintext
.
├── README.md
├── main.tf                  # Main Terraform configuration
├── variables.tf            # Input variables
├── outputs.tf             # Output definitions
└── lambda_warmer/         # Lambda function code
    └── lambda_function.py # Python implementation
```

## IAM Roles and Permissions

The module creates two separate IAM roles:

1. Lambda Role:
   - CloudWatch Logs access
   - Lambda function invocation

2. EventBridge Scheduler Role:
   - Permission to invoke the warmer Lambda function

## Schedule Expression Examples

- Every 5 minutes: `rate(5 minutes)`
- Every hour: `rate(1 hour)`
- Daily at 2 AM UTC: `cron(0 2 * * ? *)`

## Monitoring and Logs

The Lambda warmer function logs its activities to CloudWatch Logs. You can monitor:

- Functions being warmed
- Warming success/failure
- Number of functions processed
