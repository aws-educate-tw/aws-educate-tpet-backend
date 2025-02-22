aws_region                                    = "ap-northeast-1"
environment                                   = "prod"
service_underscore                            = "campaign_service"
service_hyphen                                = "campaign-service"
dynamodb_table                                = "campaign"
enable_pitr                                   = true
enable_deletion_protection_for_dynamodb_table = true
lambda_architecture = "x86_64"
