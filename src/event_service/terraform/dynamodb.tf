resource "aws_dynamodb_table" "rsvp_events" {
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

  # Support querying by item type (run / participant#...)
  global_secondary_index {
    name            = "sk-run_id-gsi"
    hash_key        = "sk"
    range_key       = "run_id"
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
