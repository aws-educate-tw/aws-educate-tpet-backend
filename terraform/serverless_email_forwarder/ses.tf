resource "aws_ses_domain_identity" "ses_aws_educate_tpet_domain" {
  domain = "aws-educate.com"
#  domain = "aws_educate_tpet.com"
}

# SES - Email Indentity
resource "aws_ses_email_identity" "ses_aws_educate_tpet_email" {
  email = var.ses_email_identity
}

# SES - Email Feedback Forwarding
resource "aws_ses_identity_feedback_forwarding_enabled" "ses_feedback_forwarding" {
  identity                 = aws_ses_domain_identity.ses_aws_educate_tpet_domain.arn
  enabled                  = true
}

resource "aws_ses_receipt_rule_set" "ses_receipt_rule_set" {
  rule_set_name = "forward_email"
}

# Add a header to the email and store it in S3
resource "aws_ses_receipt_rule" "ses_receipt_rule_forward_to_mkt" {
  name          = "forward_to_mkt" # rule name
  rule_set_name = aws_ses_receipt_rule_set.ses_receipt_rule_set.rule_set_name
  recipients    = [var.mkt_email]
  enabled       = true #  enabled receipt rules within the active rule set.
  scan_enabled  = true
  position      = 1

  s3_action {
    bucket_name = var.bucket_name
    object_key_prefix = "mkt/"
    position    = 1
  }
}

resource "aws_ses_receipt_rule" "ses_receipt_rule_forward_to_dev" {
  name          = "forward_to_dev" # rule name
  rule_set_name = aws_ses_receipt_rule_set.ses_receipt_rule_set.rule_set_name
  recipients    = [var.dev_email]
  enabled       = true #  enabled receipt rules within the active rule set.
  scan_enabled  = true
  position      = 2

  s3_action {
    bucket_name = var.bucket_name
    object_key_prefix = "dev/"
    position    = 1
  }
}

resource "aws_ses_receipt_rule" "ses_receipt_rule_forward_to_event" {
  name          = "forward_to_event" # rule name
  rule_set_name = aws_ses_receipt_rule_set.ses_receipt_rule_set.rule_set_name
  recipients    = [var.event_email]
  enabled       = true #  enabled receipt rules within the active rule set.
  scan_enabled  = true
  position      = 3

  s3_action {
    bucket_name = var.bucket_name
    object_key_prefix = "event/"
    position    = 1
  }
}

resource "aws_ses_receipt_rule" "ses_receipt_rule_forward_to_group1" {
  name          = "forward_to_group1" # rule name
  rule_set_name = aws_ses_receipt_rule_set.ses_receipt_rule_set.rule_set_name
  recipients    = [var.group1_email]
  enabled       = true #  enabled receipt rules within the active rule set.
  scan_enabled  = true
  position      = 4

  s3_action {
    bucket_name = var.bucket_name
    object_key_prefix = "group1/"
    position    = 1
  }
}

resource "aws_ses_receipt_rule" "ses_receipt_rule_forward_to_group2" {
  name          = "forward_to_group2" # rule name
  rule_set_name = aws_ses_receipt_rule_set.ses_receipt_rule_set.rule_set_name
  recipients    = [var.group2_email]
  enabled       = true #  enabled receipt rules within the active rule set.
  scan_enabled  = true
  position      = 5

  s3_action {
    bucket_name = var.bucket_name
    object_key_prefix = "group1/"
    position    = 1
  }
}


resource "aws_ses_receipt_rule" "ses_receipt_rule_forward_to_group3" {
  name          = "forward_to_group3" # rule name
  rule_set_name = aws_ses_receipt_rule_set.ses_receipt_rule_set.rule_set_name
  recipients    = [var.group1_email]
  enabled       = true #  enabled receipt rules within the active rule set.
  scan_enabled  = true
  position      = 6

  s3_action {
    bucket_name = var.bucket_name
    object_key_prefix = "group3/"
    position    = 1
  }
}

resource "aws_ses_receipt_rule" "ses_receipt_rule_forward_to_default" {
  name          = "forward_to_default" # rule name
  rule_set_name = aws_ses_receipt_rule_set.ses_receipt_rule_set.rule_set_name
  recipients    = [var.aws_educate_domain, var.aws_educate_domain_dot_prefix]
  enabled       = true #  enabled receipt rules within the active rule set.
  scan_enabled  = true
  position      = 7

  s3_action {
    bucket_name = var.bucket_name
    object_key_prefix = "default/"
    position    = 1
  }
}
