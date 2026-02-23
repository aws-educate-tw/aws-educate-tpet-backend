# EventBridge rule to monitor CloudWatch alarm state changes
resource "aws_cloudwatch_event_rule" "alarm_state_change" {
  name        = "${var.environment}-alarm-state-change"
  description = "Capture CloudWatch alarm state changes to auto re-enable actions"

  event_pattern = jsonencode({
    source      = ["aws.cloudwatch"]
    detail-type = ["CloudWatch Alarm State Change"]
  })

  tags = {
    Environment = var.environment
    Terraform   = "true"
  }
}

# EventBridge target pointing to auto re-enable Lambda
resource "aws_cloudwatch_event_target" "auto_reenable_lambda" {
  rule      = aws_cloudwatch_event_rule.alarm_state_change.name
  target_id = "AutoReenableLambda"
  arn       = module.auto_reenable_lambda.lambda_function_arn
}

# Permission for EventBridge to invoke Lambda
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = module.auto_reenable_lambda.lambda_function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.alarm_state_change.arn
}
