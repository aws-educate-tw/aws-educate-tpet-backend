resource "aws_ses_domain_identity" "ses_aws_educate_tpet_domain" {
  domain = var.domain_name
}

# SES - Email Indentity
resource "aws_ses_email_identity" "ses_aws_educate_tpet_email" {
  email = var.ses_email_identity
}

resource "aws_ses_receipt_rule_set" "ses_receipt_rule_set" {
  rule_set_name = "${var.environment}-forward-email-rule-set"
}

<<<<<<< HEAD
resource "aws_ses_receipt_rule" "ses_receipt_rule_forward_to_dev" {
  name          = "forward_to_dev" # rule name
  rule_set_name = aws_ses_receipt_rule_set.ses_receipt_rule_set.rule_set_name
  recipients    = [var.dev_email]
  enabled       = true #  enabled receipt rules within the active rule set.
  scan_enabled  = true

  s3_action {
    bucket_name       = local.bucket_name
    object_key_prefix = "dev/"
    position          = 1
  }
}

resource "aws_ses_receipt_rule" "ses_receipt_rule_forward_to_contact" {
  name          = "forward_to_contact" # rule name
  rule_set_name = aws_ses_receipt_rule_set.ses_receipt_rule_set.rule_set_name
  recipients    = [var.contact_email]
  enabled       = true #  enabled receipt rules within the active rule set.
  scan_enabled  = true

  s3_action {
    bucket_name       = local.bucket_name
    object_key_prefix = "contact/"
    position          = 2
  }
}

=======
>>>>>>> 07ee99ddc50c88df75abe3a9e9167d3055c0542d
# Add a header to the email and store it in S3
resource "aws_ses_receipt_rule" "ses_receipt_rule_forward_to_mkt" {
  name          = "forward_to_mkt" # rule name
  rule_set_name = aws_ses_receipt_rule_set.ses_receipt_rule_set.rule_set_name
  recipients    = [var.mkt_email]
  enabled       = true #  enabled receipt rules within the active rule set.
  scan_enabled  = true

  s3_action {
<<<<<<< HEAD
    bucket_name       = local.bucket_name
    object_key_prefix = "mkt/"
    position          = 3
  }

=======
    bucket_name       = aws_s3_bucket.aws_educate_tpet_email_bucket.id
    object_key_prefix = "mkt/"
    position          = 1
  }

  depends_on = [
    aws_s3_bucket.aws_educate_tpet_email_bucket,
    aws_s3_bucket_policy.ses_put_object
  ]
>>>>>>> 07ee99ddc50c88df75abe3a9e9167d3055c0542d
}

resource "aws_ses_receipt_rule" "ses_receipt_rule_forward_to_tech" {
  name          = "forward_to_tech" # rule name
  rule_set_name = aws_ses_receipt_rule_set.ses_receipt_rule_set.rule_set_name
  recipients    = [var.tech_email]
  enabled       = true #  enabled receipt rules within the active rule set.
  scan_enabled  = true

  s3_action {
<<<<<<< HEAD
    bucket_name       = local.bucket_name
    object_key_prefix = "tech/"
    position          = 4
  }

=======
    bucket_name       = aws_s3_bucket.aws_educate_tpet_email_bucket.id
    object_key_prefix = "tech/"
    position          = 1
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
    bucket_name       = aws_s3_bucket.aws_educate_tpet_email_bucket.id
    object_key_prefix = "dev/"
    position          = 1
  }

  depends_on = [
    aws_s3_bucket.aws_educate_tpet_email_bucket,
    aws_s3_bucket_policy.ses_put_object
  ]
>>>>>>> 07ee99ddc50c88df75abe3a9e9167d3055c0542d
}

resource "aws_ses_receipt_rule" "ses_receipt_rule_forward_to_event" {
  name          = "forward_to_event" # rule name
  rule_set_name = aws_ses_receipt_rule_set.ses_receipt_rule_set.rule_set_name
  recipients    = [var.event_email]
  enabled       = true #  enabled receipt rules within the active rule set.
  scan_enabled  = true

  s3_action {
<<<<<<< HEAD
    bucket_name       = local.bucket_name
    object_key_prefix = "event/"
    position          = 5
  }
=======
    bucket_name       = aws_s3_bucket.aws_educate_tpet_email_bucket.id
    object_key_prefix = "event/"
    position          = 1
  }

  depends_on = [
    aws_s3_bucket.aws_educate_tpet_email_bucket,
    aws_s3_bucket_policy.ses_put_object
  ]
>>>>>>> 07ee99ddc50c88df75abe3a9e9167d3055c0542d
}

resource "aws_ses_receipt_rule" "ses_receipt_rule_forward_to_group1" {
  name          = "forward_to_group1" # rule name
  rule_set_name = aws_ses_receipt_rule_set.ses_receipt_rule_set.rule_set_name
  recipients    = [var.group1_email]
  enabled       = true #  enabled receipt rules within the active rule set.
  scan_enabled  = true

  s3_action {
<<<<<<< HEAD
    bucket_name       = local.bucket_name
    object_key_prefix = "group1/"
    position          = 6
  }
=======
    bucket_name       = aws_s3_bucket.aws_educate_tpet_email_bucket.id
    object_key_prefix = "group1/"
    position          = 1
  }

  depends_on = [
    aws_s3_bucket.aws_educate_tpet_email_bucket,
    aws_s3_bucket_policy.ses_put_object
  ]
>>>>>>> 07ee99ddc50c88df75abe3a9e9167d3055c0542d
}

resource "aws_ses_receipt_rule" "ses_receipt_rule_forward_to_group2" {
  name          = "forward_to_group2" # rule name
  rule_set_name = aws_ses_receipt_rule_set.ses_receipt_rule_set.rule_set_name
  recipients    = [var.group2_email]
  enabled       = true #  enabled receipt rules within the active rule set.
  scan_enabled  = true

  s3_action {
<<<<<<< HEAD
    bucket_name       = local.bucket_name
    object_key_prefix = "group2/"
    position          = 7
  }
}

=======
    bucket_name       = aws_s3_bucket.aws_educate_tpet_email_bucket.id
    object_key_prefix = "group2/"
    position          = 1
  }

  depends_on = [
    aws_s3_bucket.aws_educate_tpet_email_bucket,
    aws_s3_bucket_policy.ses_put_object
  ]
}


>>>>>>> 07ee99ddc50c88df75abe3a9e9167d3055c0542d
resource "aws_ses_receipt_rule" "ses_receipt_rule_forward_to_group3" {
  name          = "forward_to_group3" # rule name
  rule_set_name = aws_ses_receipt_rule_set.ses_receipt_rule_set.rule_set_name
  recipients    = [var.group3_email]
  enabled       = true #  enabled receipt rules within the active rule set.
  scan_enabled  = true

  s3_action {
<<<<<<< HEAD
    bucket_name       = local.bucket_name
    object_key_prefix = "group3/"
    position          = 8
  }
=======
    bucket_name       = aws_s3_bucket.aws_educate_tpet_email_bucket.id
    object_key_prefix = "group3/"
    position          = 1
  }

  depends_on = [
    aws_s3_bucket.aws_educate_tpet_email_bucket,
    aws_s3_bucket_policy.ses_put_object
  ]
>>>>>>> 07ee99ddc50c88df75abe3a9e9167d3055c0542d
}

resource "aws_ses_receipt_rule" "ses_receipt_rule_forward_to_default" {
  name          = "forward_to_default" # rule name
  rule_set_name = aws_ses_receipt_rule_set.ses_receipt_rule_set.rule_set_name
  recipients    = [var.aws_educate_domain, var.aws_educate_domain_dot_prefix]
  enabled       = true #  enabled receipt rules within the active rule set.
  scan_enabled  = true

  s3_action {
<<<<<<< HEAD
    bucket_name       = local.bucket_name
    object_key_prefix = "default/"
    position          = 9
  }
}

resource "aws_ses_active_receipt_rule_set" "ses_active_receipt_rule_set" {
  rule_set_name = aws_ses_receipt_rule_set.ses_receipt_rule_set.rule_set_name

  depends_on = [
    aws_ses_receipt_rule.ses_receipt_rule_forward_to_dev,
    aws_ses_receipt_rule.ses_receipt_rule_forward_to_contact,
    aws_ses_receipt_rule.ses_receipt_rule_forward_to_mkt,
    aws_ses_receipt_rule.ses_receipt_rule_forward_to_tech,
    aws_ses_receipt_rule.ses_receipt_rule_forward_to_event,
    aws_ses_receipt_rule.ses_receipt_rule_forward_to_group1,
    aws_ses_receipt_rule.ses_receipt_rule_forward_to_group2,
    aws_ses_receipt_rule.ses_receipt_rule_forward_to_group3,
    aws_ses_receipt_rule.ses_receipt_rule_forward_to_default
=======
    bucket_name       = aws_s3_bucket.aws_educate_tpet_email_bucket.id
    object_key_prefix = "default/"
    position          = 1
  }

  depends_on = [
    aws_s3_bucket.aws_educate_tpet_email_bucket,
    aws_s3_bucket_policy.ses_put_object
>>>>>>> 07ee99ddc50c88df75abe3a9e9167d3055c0542d
  ]
}
