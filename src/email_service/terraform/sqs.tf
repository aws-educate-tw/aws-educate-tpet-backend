module "send_email_sqs" {
  source  = "terraform-aws-modules/sqs/aws"
  version = "4.2.0"

  name                       = "${var.environment}-send-email-sqs"
  visibility_timeout_seconds = 320 # Second, make sure it is larger than the Lambda timeout
}
