resource "aws_dynamodb_table" "file" {
  name         = "file"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "file_id"

  attribute {
    name = "file_id"
    type = "S"
  }

  tags = {
    Name = "file"
  }
}
