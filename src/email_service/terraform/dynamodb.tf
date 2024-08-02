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

  deletion_protection_enabled = var.enable_deletion_protection_for_dynamodb_table

  point_in_time_recovery {
    enabled = var.enable_pitr
  }

  tags = {
    Name = "email"
  }
}

resource "aws_dynamodb_table" "run" {
  name         = "run"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "run_id"

  attribute {
    name = "run_id"
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

  global_secondary_index {
    name            = "created_year_created_at_gsi"
    hash_key        = "created_year"
    range_key       = "created_at"
    projection_type = "ALL"
  }


  deletion_protection_enabled = var.enable_deletion_protection_for_dynamodb_table

  point_in_time_recovery {
    enabled = var.enable_pitr
  }

  tags = {
    Name = "run"
  }
}


resource "aws_dynamodb_table" "email_service_pagination_state" {
  name         = "email_service_pagination_state"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"
  range_key    = "index_name"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "index_name"
    type = "S"
  }

  deletion_protection_enabled = var.enable_deletion_protection_for_dynamodb_table

  point_in_time_recovery {
    enabled = var.enable_pitr
  }


  tags = {
    Name = "email_service_pagination_state"
  }
}
