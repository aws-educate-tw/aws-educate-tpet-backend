aws_region                                    = "us-east-1"
environment                                   = "dev"
service_underscore                            = "webhook_service"
service_hyphen                                = "webhook-service"
dynamodb_table                                = "webhook"
enable_pitr                                   = true
enable_deletion_protection_for_dynamodb_table = true
docker_host                                   = "unix:///Users/chungchihhan/.docker/run/docker.sock"
