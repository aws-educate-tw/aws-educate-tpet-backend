aws_region                                    = "ap-northeast-1"
environment                                   = "prod"
service_underscore                            = "webhook_service"
service_hyphen                                = "webhook-service"
dynamodb_table                                = "webhook"
dynamodb_table_total_count                    = "webhook_total_count"
enable_pitr                                   = true
enable_deletion_protection_for_dynamodb_table = true
docker_host                                   = "unix:///Users/chungchihhan/.docker/run/docker.sock"

