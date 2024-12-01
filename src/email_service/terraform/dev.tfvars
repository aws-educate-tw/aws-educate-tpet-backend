aws_region                                    = "us-east-1"
environment                                   = "dev"
service_underscore                            = "email_service"
service_hyphen                                = "email-service"
dynamodb_table                                = "email"
run_dynamodb_table                            = "run"
pagination_state_dynamodb_table               = "email_service_pagination_state"
enable_pitr                                   = false
enable_deletion_protection_for_dynamodb_table = true
