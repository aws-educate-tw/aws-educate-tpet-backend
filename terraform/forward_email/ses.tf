resource "aws_ses_domain_identity" "ses_aws_educate_tpet_domain" {
  domain = var.domain_name
}

# SES - Email Indentity
resource "aws_ses_email_identity" "ses_aws_educate_tpet_email" {
  email = var.ses_email_identity
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

  s3_action {
    bucket_name = var.bucket_name
    object_key_prefix = "mkt/"
    position    = 1
  }

  depends_on = [
    aws_s3_bucket.aws_educate_tpet_email_bucket,
    aws_s3_bucket_policy.ses_put_object
  ]
}

resource "aws_ses_receipt_rule" "ses_receipt_rule_forward_to_tech" {
  name          = "forward_to_tech" # rule name
  rule_set_name = aws_ses_receipt_rule_set.ses_receipt_rule_set.rule_set_name
  recipients    = [var.tech_email]
  enabled       = true #  enabled receipt rules within the active rule set.
  scan_enabled  = true

  s3_action {
    bucket_name = var.bucket_name
    object_key_prefix = "tech/"
    position    = 1
  }

  depends_on = [
    aws_s3_bucket.aws_educate_tpet_email_bucket,
    aws_s3_bucket_policy.ses_put_object
  ]
}

resource "aws_ses_receipt_rule" "ses_receipt_rule_forward_to_dev" {
  name          = "forward_to_dev" # rule name
  rule_set_name = aws_ses_receipt_rule_set.ses_receipt_rule_set.rule_set_name
  recipients    = [var.dev_email]
  enabled       = true #  enabled receipt rules within the active rule set.
  scan_enabled  = true

  s3_action {
    bucket_name = var.bucket_name
    object_key_prefix = "dev/"
    position    = 1
  }

  depends_on = [
    aws_s3_bucket.aws_educate_tpet_email_bucket,
    aws_s3_bucket_policy.ses_put_object
  ]
}

resource "aws_ses_receipt_rule" "ses_receipt_rule_forward_to_event" {
  name          = "forward_to_event" # rule name
  rule_set_name = aws_ses_receipt_rule_set.ses_receipt_rule_set.rule_set_name
  recipients    = [var.event_email]
  enabled       = true #  enabled receipt rules within the active rule set.
  scan_enabled  = true

  s3_action {
    bucket_name = var.bucket_name
    object_key_prefix = "event/"
    position    = 1
  }

  depends_on = [
    aws_s3_bucket.aws_educate_tpet_email_bucket,
    aws_s3_bucket_policy.ses_put_object
  ]
}

resource "aws_ses_receipt_rule" "ses_receipt_rule_forward_to_group1" {
  name          = "forward_to_group1" # rule name
  rule_set_name = aws_ses_receipt_rule_set.ses_receipt_rule_set.rule_set_name
  recipients    = [var.group1_email]
  enabled       = true #  enabled receipt rules within the active rule set.
  scan_enabled  = true

  s3_action {
    bucket_name = var.bucket_name
    object_key_prefix = "group1/"
    position    = 1
  }

  depends_on = [
    aws_s3_bucket.aws_educate_tpet_email_bucket,
    aws_s3_bucket_policy.ses_put_object
  ]
}

resource "aws_ses_receipt_rule" "ses_receipt_rule_forward_to_group2" {
  name          = "forward_to_group2" # rule name
  rule_set_name = aws_ses_receipt_rule_set.ses_receipt_rule_set.rule_set_name
  recipients    = [var.group2_email]
  enabled       = true #  enabled receipt rules within the active rule set.
  scan_enabled  = true

  s3_action {
    bucket_name = var.bucket_name
    object_key_prefix = "group2/"
    position    = 1
  }

  depends_on = [
    aws_s3_bucket.aws_educate_tpet_email_bucket,
    aws_s3_bucket_policy.ses_put_object
  ]
}


resource "aws_ses_receipt_rule" "ses_receipt_rule_forward_to_group3" {
  name          = "forward_to_group3" # rule name
  rule_set_name = aws_ses_receipt_rule_set.ses_receipt_rule_set.rule_set_name
  recipients    = [var.group3_email]
  enabled       = true #  enabled receipt rules within the active rule set.
  scan_enabled  = true

  s3_action {
    bucket_name = var.bucket_name
    object_key_prefix = "group3/"
    position    = 1
  }

  depends_on = [
    aws_s3_bucket.aws_educate_tpet_email_bucket,
    aws_s3_bucket_policy.ses_put_object
  ]
}

resource "aws_ses_receipt_rule" "ses_receipt_rule_forward_to_default" {
  name          = "forward_to_default" # rule name
  rule_set_name = aws_ses_receipt_rule_set.ses_receipt_rule_set.rule_set_name
  recipients    = [var.aws_educate_domain, var.aws_educate_domain_dot_prefix]
  enabled       = true #  enabled receipt rules within the active rule set.
  scan_enabled  = true

  s3_action {
    bucket_name = var.bucket_name
    object_key_prefix = "default/"
    position    = 1
  }

  depends_on = [
    aws_s3_bucket.aws_educate_tpet_email_bucket,
    aws_s3_bucket_policy.ses_put_object
  ]
}