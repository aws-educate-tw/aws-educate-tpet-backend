aws_region                                    = "us-east-1"
environment                                   = "dev"
service_underscore                            = "file_service"
service_hyphen                                = "file-service"
dynamodb_table                                = "file"
enable_pitr                                   = true
enable_deletion_protection_for_dynamodb_table = true
lambda_architecture = "x86_64"
