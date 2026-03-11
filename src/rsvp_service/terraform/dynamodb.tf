resource "aws_dynamodb_table" "campaigns" {
  name         = "Campaigns"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "campaign_id"

  attribute {
    name = "campaign_id"
    type = "S"
  }

  deletion_protection_enabled = var.enable_deletion_protection_for_dynamodb_table

  point_in_time_recovery {
    enabled = var.enable_pitr
  }

  tags = {
    Name = "Campaigns"
  }
}

resource "aws_dynamodb_table" "runs_campaigns_mapping" {
  name         = "runs_campaigns_mapping"
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
    Name = "runs_campaigns_mapping"
  }
}

resource "aws_dynamodb_table" "participants" {
  name         = "participants"
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
    name            = "gsi_campaign_participant_uniq_handle_created_at"
    hash_key        = "campaign_participant_uniq_handle"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  deletion_protection_enabled = var.enable_deletion_protection_for_dynamodb_table

  point_in_time_recovery {
    enabled = var.enable_pitr
  }

  tags = {
    Name = "participants"
  }
}
