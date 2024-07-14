resource "aws_dynamodb_table" "campaign" {
  name         = "campaign"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "campaign_id"

  attribute {
    name = "campaign_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  global_secondary_index {
    name            = "campaign_id-created_at-gsi"
    hash_key        = "campaign_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  tags = {
    Name = "campaign"
  }
}
