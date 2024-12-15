resource "aws_dynamodb_table" "webhook" {
  name         = "webhook"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "webhook_id"

  attribute {
    name = "webhook_id"
    type = "S"
  }

  attribute {
    name = "sequence_number"
    type = "N"
  }

  attribute {
    name = "webhook_type"
    type = "S"
  }

  global_secondary_index {
    name               = "SequenceNumberIndex" # Updated GSI name
    hash_key           = "webhook_type"        # Partition key
    range_key          = "sequence_number"     # Sort key
    projection_type    = "ALL"                 # Include all attributes in the GSI
  }

  tags = {
    Name = "webhook"
  }
}

resource "aws_dynamodb_table" "webhook_total_count" {
  name         = "webhook_total_count"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "webhook_type"

  attribute {
    name = "webhook_type"
    type = "S"
  }

  tags = {
    Name = "webhook"
  }
}
