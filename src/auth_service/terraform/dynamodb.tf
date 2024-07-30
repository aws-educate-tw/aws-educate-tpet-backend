resource "aws_dynamodb_table" "user" {
  name         = "user"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "username"
    type = "S"
  }

  attribute {
    name = "email"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  attribute {
    name = "last_login_at"
    type = "S"
  }

  global_secondary_index {
    name            = "user_id-created_at-gsi"
    hash_key        = "user_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }


  global_secondary_index {
    name            = "user_id-last_login_at-gsi"
    hash_key        = "user_id"
    range_key       = "last_login_at"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "email-last_login_at-gsi"
    hash_key        = "email"
    range_key       = "last_login_at"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "username-last_login_at-gsi"
    hash_key        = "username"
    range_key       = "last_login_at"
    projection_type = "ALL"
  }

  deletion_protection_enabled = var.enable_deletion_protection_for_dynamodb_table

  point_in_time_recovery {
    enabled = var.enable_pitr
  }

  tags = {
    Name = "user"
  }
}
