resource "aws_dynamodb_table" "email" {
  name         = "email"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "run_id"
  range_key    = "email_id"

  attribute {
    name = "run_id"
    type = "S"
  }

  attribute {
    name = "email_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  global_secondary_index {
    name            = "run_id-status-gsi"
    hash_key        = "run_id"
    range_key       = "status"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "run_id-created_at-gsi"
    hash_key        = "run_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  tags = {
    Name = "email"
  }
}
