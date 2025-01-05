aws_region                                    = "us-west-1"
environment                                   = "preview"
service_underscore                            = "webhook_service"
service_hyphen                                = "webhook-service"
dynamodb_table                                = "webhook"
enable_pitr                                   = false
enable_deletion_protection_for_dynamodb_table = false
docker_host                                   = "unix:///var/run/docker.sock"
