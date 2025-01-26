module "list_files" {
  source      = "./../src/file_service/terraform"
  aws_region  = var.aws_region
  environment = var.environment
}
