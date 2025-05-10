resource "null_resource" "init_database" {
  provisioner "local-exec" {
    command = <<EOT
      aws rds-data execute-statement \
        --region ${var.aws_region} \
        --resource-arn "${module.aurora_postgresql_v2.cluster_arn}" \
        --secret-arn "${module.aurora_postgresql_v2.cluster_master_user_secret[0]["secret_arn"]}" \
        --database "postgres" \
        --sql "CREATE DATABASE ${var.database_name};" \
    EOT
  }

  triggers = {
    always_run = timestamp()
  }
}

resource "null_resource" "init_schema" {
  depends_on = [null_resource.init_database]

  provisioner "local-exec" {
    command = "bash init-schema.sh ${module.aurora_postgresql_v2.cluster_arn} ${module.aurora_postgresql_v2.cluster_master_user_secret[0]["secret_arn"]} ${var.database_name} ${var.aws_region}"
  }

  triggers = {
    always_run = timestamp()
  }
}
