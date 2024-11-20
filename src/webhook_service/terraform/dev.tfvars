aws_region                                    = "us-east-1"
environment                                   = "dev"
service_underscore                            = "webhook_service"
service_hyphen                                = "webhook-service"
dynamodb_table                                = "webhook"
send_email_api_endpoint                       = "https://api.tpet.aws-educate.tw/${environment}/send-email"
enable_pitr                                   = false
enable_deletion_protection_for_dynamodb_table = false
