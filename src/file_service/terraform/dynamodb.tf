resource "aws_dynamodb_table" "file" {
  name         = "file"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "file_id"

  attribute {
    name = "file_id"
    type = "S"
  }

  attribute {
    name = "file_extension"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  attribute {
    name = "created_year"
    type = "S"
  }

  attribute {
    name = "created_year_month"
    type = "S"
  }

  attribute {
    name = "created_year_month_day"
    type = "S"
  }

  global_secondary_index {
    name            = "file_extension-created_at-gsi"
    hash_key        = "file_extension"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "created_year_created_at_gsi"
    hash_key        = "created_year"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "created_year_month_created_at_gsi"
    hash_key        = "created_year_month"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "created_year_month_day_created_at_gsi"
    hash_key        = "created_year_month_day"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  tags = {
    Name = "file"
  }
}

resource "aws_dynamodb_table" "file_service_pagination_state" {
  name         = "file_service_pagination_state"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  tags = {
    Name = "file_service_pagination_state"
  }
}
