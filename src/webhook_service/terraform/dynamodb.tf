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

  # The order of sequence_number is the same as the order of ascending order of created_at
  # So sorting by sequence_number is the same as sorting by created_at, we only need to use SequenceNumberIndex to sort here.
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

  deletion_protection_enabled = var.enable_deletion_protection_for_dynamodb_table  

  point_in_time_recovery {  
    enabled = var.enable_pitr  
  }  
  
  tags = {
    Name = "webhook"
  }
}
