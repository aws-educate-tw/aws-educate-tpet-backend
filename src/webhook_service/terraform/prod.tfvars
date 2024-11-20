aws_region                                    = "ap-northeast-1"
environment                                   = "prod"
service_underscore                            = "webhook_service"
service_hyphen                                = "webhook-service"
dynamodb_table                                = "webhook"
send_email_api_endpoint                       = "https://api.tpet.aws-educate.tw/${environment}/send-email"
enable_pitr                                   = true
enable_deletion_protection_for_dynamodb_table = true

