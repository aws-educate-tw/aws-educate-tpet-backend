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

  global_secondary_index {
    name            = "file_extension-created_at-gsi"
    hash_key        = "file_extension"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  tags = {
    Name = "file"
  }
}
