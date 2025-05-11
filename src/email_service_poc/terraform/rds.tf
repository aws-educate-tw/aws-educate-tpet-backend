data "aws_rds_engine_version" "postgresql" {
  engine  = "aurora-postgresql"
  version = "16.6"
}

module "aurora_postgresql_v2" {
  source = "terraform-aws-modules/rds-aurora/aws"

  name              = "${var.environment}-${var.service_hyphen}-aurora-postgresql-v2"
  engine            = data.aws_rds_engine_version.postgresql.engine
  engine_mode       = "provisioned"
  engine_version    = data.aws_rds_engine_version.postgresql.version
  storage_encrypted = true
  manage_master_user_password = true
  master_username = "postgres"

  vpc_id               = module.vpc.vpc_id
  db_subnet_group_name = module.vpc.database_subnet_group_name

  monitoring_interval     = 60
  apply_immediately       = true
  skip_final_snapshot     = true
  enable_http_endpoint    = true

  serverlessv2_scaling_configuration = {
    min_capacity             = 0
    max_capacity             = 1
    seconds_until_auto_pause = 300
  }

  instance_class = "db.serverless"
  instances = {
    one = {}
    # two = {}
  }

  tags = local.tags
}
