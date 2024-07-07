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

  local_secondary_index {
    name            = "status_lsi"
    projection_type = "ALL"
    range_key       = "status"
  }

  local_secondary_index {
    name            = "create_at_lsi"
    projection_type = "ALL"
    range_key       = "created_at"
  }

  tags = {
    Name    = "email"
    Creator = "Richie"
  }
}
