resource "aws_dynamodb_table" "webhook" {
  name         = "webhook"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "webhook_id"

  attribute {
    name = "webhook_id"
    type = "S"
  }

  tags = {
    Name = "webhook"
  }
}
