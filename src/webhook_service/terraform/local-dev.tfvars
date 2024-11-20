aws_region                                    = "us-west-2"
environment                                   = "local-dev"
service_underscore                            = "webhook_service"
service_hyphen                                = "webhook-service"
dynamodb_table                                = "webhook"
send_email_api_endpoint                       = "https://${environment}-email-service-internal-api-tpet.aws-educate.tw/${environment}/send-email"
enable_pitr                                   = false
enable_deletion_protection_for_dynamodb_table = false
