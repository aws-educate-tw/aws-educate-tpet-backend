aws_region                                    = "us-east-1"
environment                                   = "dev"
service_underscore                            = "webhook_service"
service_hyphen                                = "webhook-service"
dynamodb_table                                = "webhook"
dynamodb_table_total_count                    = "webhook_total_count"
enable_pitr                                   = false
enable_deletion_protection_for_dynamodb_table = true
docker_host                                   = "unix:///var/run/docker.sock"