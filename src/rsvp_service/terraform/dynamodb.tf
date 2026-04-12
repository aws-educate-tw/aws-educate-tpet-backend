resource "aws_dynamodb_table" "campaigns" {
  name         = "campaign"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "cohort"
  range_key    = "campaign_id-created_at"

  attribute {
    name = "cohort"
    type = "S"
  }

  attribute {
    name = "campaign_id-created_at"
    type = "S"
  }

  deletion_protection_enabled = var.enable_deletion_protection_for_dynamodb_table

  point_in_time_recovery {
    enabled = var.enable_pitr
  }

  tags = {
    Name = "campaign"
  }
}

resource "aws_dynamodb_table" "campaign_run" {
  name         = "campaign_run"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "campaign_id"
  range_key    = "run_id"

  attribute {
    name = "campaign_id"
    type = "S"
  }

  attribute {
    name = "run_id"
    type = "S"
  }

  deletion_protection_enabled = var.enable_deletion_protection_for_dynamodb_table

  point_in_time_recovery {
    enabled = var.enable_pitr
  }

  tags = {
    Name = "campaign_run"
  }
}

resource "aws_dynamodb_table" "participants" {
  name         = "participant"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "run_id"
  range_key    = "participant_id"

  attribute {
    name = "run_id"
    type = "S"
  }

  attribute {
    name = "participant_id"
    type = "S"
  }

  attribute {
    name = "campaign_participant_uniq_handle"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  global_secondary_index {
    name            = "participant-campaign_participant_uniq_handle-created_at-gsi"
    hash_key        = "campaign_participant_uniq_handle"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  deletion_protection_enabled = var.enable_deletion_protection_for_dynamodb_table

  point_in_time_recovery {
    enabled = var.enable_pitr
  }

  tags = {
    Name = "participant"
  }
}
