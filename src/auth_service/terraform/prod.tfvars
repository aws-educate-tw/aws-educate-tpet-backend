aws_region                                    = "ap-northeast-1"
environment                                   = "prod"
service_underscore                            = "auth_service"
service_hyphen                                = "auth-service"
dynamodb_table                                = "user"
enable_pitr                                   = true
enable_deletion_protection_for_dynamodb_table = true
lambda_architecture = "x86_64"
