module "create_email_sqs" {
  source  = "terraform-aws-modules/sqs/aws"
  version = "4.2.0"

  name                       = "${var.environment}-create-eamil-sqs"
  visibility_timeout_seconds = 3600 # Second, make sure it is larger than the Lambda timeout

  # Dead letter queue
  create_dlq = true
  redrive_policy = {
    # One failure to receive a message would cause the message to move to the DLQ
    maxReceiveCount = 2
  }
}


module "send_email_sqs" {
  source  = "terraform-aws-modules/sqs/aws"
  version = "4.2.0"

  name                       = "${var.environment}-send-email-sqs"
  visibility_timeout_seconds = 610 # Second, make sure it is larger than the Lambda timeout

  # Dead letter queue
  create_dlq = true
  redrive_policy = {
    # One failure to receive a message would cause the message to move to the DLQ
    maxReceiveCount = 2
  }
}
