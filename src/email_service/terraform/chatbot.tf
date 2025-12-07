# IAM Policy for Chatbot DLQ Channel
resource "aws_iam_policy" "dlq_channel_policy" {
  name        = "${var.environment}-email-service-dlq-chatbot-policy"
  description = "Policy for AWS Chatbot to manage DLQ operations"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Sid    = "AllowSQSReceiveAndRedrive"
        Action = [
          "sqs:StartMessageMoveTask",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = module.auto_resumer_sqs.dead_letter_queue_arn
      },
      {
        Effect = "Allow"
        Sid    = "AllowRedrive"
        Action = [
          "sqs:SendMessage"
        ]
        Resource = module.auto_resumer_sqs.queue_arn
      },
      {
        Effect = "Allow"
        Sid    = "AllowCloudWatchReadOnly"
        Action = [
          "cloudwatch:Describe*",
          "cloudwatch:Get*",
          "cloudwatch:List*"
        ]
        Resource = "*"
      }
    ]
  })
}

# IAM Role for Chatbot
resource "aws_iam_role" "dlq_channel_role" {
  name = "${var.environment}-email-service-dlq-chatbot-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "chatbot.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "dlq_channel_policy_attachment" {
  role       = aws_iam_role.dlq_channel_role.name
  policy_arn = aws_iam_policy.dlq_channel_policy.arn
}

# Slack Channel Configuration
resource "awscc_chatbot_slack_channel_configuration" "dlq_management" {
  configuration_name = "${var.environment}-email-service-dlq-management"
  iam_role_arn       = aws_iam_role.dlq_channel_role.arn
  slack_channel_id   = var.slack_channel_id
  slack_workspace_id = var.slack_workspace_id

  guardrail_policies = [
    aws_iam_policy.dlq_channel_policy.arn
  ]

  sns_topic_arns = [
    aws_sns_topic.dlq_notifications.arn
  ]

  # Note: AWS Chatbot Custom Actions are not yet supported in Terraform
  # You'll need to create these manually in the AWS Console or use CloudFormation for:
  # 1. DLQ-Message-Peek custom action
  # 2. DLQ-Message-Redrive custom action
  # 
  # Peek command: sqs receive-message --region ${region} --queue-url ${dlq_url} --max-number-of-messages 1 --wait-time-seconds 0 --visibility-timeout 0 --query "Messages[0].Body"
  # Redrive command: sqs start-message-move-task --source-arn ${dlq_arn}
}
