# Secret for surveycake service account access token
resource "aws_secretsmanager_secret" "surveycake_service_account_access_token" {
  name        = "aws-educate-tpet/${var.environment}/service-accounts/surveycake/access-token"
  description = "Access token for AWS Eudcate TPET ${var.environment} SurveyCake service account"

  tags = {
    Service = var.service_underscore
  }

  # Resource Policy
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowWebhookServiceToReadSecret"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:PrincipalTag/Service" : "webhook_service",
            "aws:PrincipalTag/Environment" : var.environment
          }
        }
      },
      {
        Sid    = "AllowTokenRefreshFunctionToManageSecret"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:UpdateSecret"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:PrincipalTag/Service" : "auth_service",
            "aws:PrincipalTag/Environment" : var.environment
          }
        }
      }
    ]
  })

  # Prevent deletion of this Secret
  lifecycle {
    prevent_destroy = true
  }
}

# Store initial surveycake access token (empty)
resource "aws_secretsmanager_secret_version" "surveycake_access_token" {
  secret_id = aws_secretsmanager_secret.surveycake_service_account_access_token.id
  secret_string = jsonencode({
    account      = "surveycake"
    access_token = ""
  })
}

# Secret for postman service account access token
resource "aws_secretsmanager_secret" "postman_service_account_access_token" {
  name        = "aws-educate-tpet/${var.environment}/service-accounts/postman/access-token"
  description = "Access token for AWS Eudcate TPET ${var.environment} Postman service account"

  tags = {
    Service = var.service_underscore
  }

  # Resource Policy
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowWebhookServiceToReadSecret"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:PrincipalTag/Service" : "webhook_service",
            "aws:PrincipalTag/Environment" : var.environment
          }
        }
      },
      {
        Sid    = "AllowTokenRefreshFunctionToManageSecret"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:UpdateSecret"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:PrincipalTag/Service" : "auth_service",
            "aws:PrincipalTag/Environment" : var.environment
          }
        }
      }
    ]
  })

  # Prevent deletion of this Secret
  lifecycle {
    prevent_destroy = true
  }
}

# Store initial postman access token (empty)
resource "aws_secretsmanager_secret_version" "postman_access_token" {
  secret_id = aws_secretsmanager_secret.postman_service_account_access_token.id
  secret_string = jsonencode({
    account      = "postman"
    access_token = ""
  })
}
