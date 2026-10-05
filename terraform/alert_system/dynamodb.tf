resource "aws_dynamodb_table" "alarm_slack_mapping" {
  name           = "${var.environment}-alarm-slack-mapping"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "alarm_key"

  attribute {
    name = "alarm_key"
    type = "S"
  }

  ttl {
    enabled        = true
    attribute_name = "ttl"
  }

  tags = {
    Name        = "${var.environment}-alarm-slack-mapping"
    Environment = var.environment
    Terraform   = "true"
  }
}
