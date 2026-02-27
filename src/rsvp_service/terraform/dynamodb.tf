resource "aws_dynamodb_table" "rsvp_campaigns" {
  name         = var.dynamodb_table
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "run_id"
  range_key    = "sk"

  attribute {
    name = "run_id"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  attribute {
    name = "event_id"
    type = "S"
  }

  # Support querying runs by event_id
  global_secondary_index {
    name            = "gsi_event_lookup"
    hash_key        = "event_id"
    range_key       = "sk"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  deletion_protection_enabled = var.enable_deletion_protection_for_dynamodb_table

  point_in_time_recovery {
    enabled = var.enable_pitr
  }

  tags = {
    Name = var.dynamodb_table
  }
}

resource "aws_dynamodb_table" "campaigns" {
  name         = var.campaigns_table
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "event_id"

  attribute {
    name = "event_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  deletion_protection_enabled = var.enable_deletion_protection_for_dynamodb_table

  point_in_time_recovery {
    enabled = var.enable_pitr
  }

  tags = {
    Name = var.campaigns_table
  }
}
