
data "aws_ecr_authorization_token" "token" {}
data "aws_caller_identity" "this" {}

locals {
  source_path   = "${path.module}/.."
  function_name = "onboarding_ariel"
  ecr_repo_name = "onboarding_ariel"

  files_include = fileset(local.source_path, "get_intro/**")
  dir_sha = sha1(join("", [for f in local.files_include : filesha1("${local.source_path}/${f}")]))
}

module "onboarding_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.0"

  function_name  = local.function_name
  description    = "Ariel Onboarding in ${var.environment}"
  create_package = false

  package_type  = "Image"
  architectures = [var.lambda_architecture]
  image_uri     = module.onboarding_docker_image.image_uri
  publish       = true

  allowed_triggers = {
    AllowExecutionFromAPIGateway = {
      service    = "apigateway"
      source_arn = "${aws_api_gateway_rest_api.onboarding_api.execution_arn}/*/*"
    }
  }
}


module "onboarding_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.7.0"

  create_ecr_repo = true
  ecr_repo        = local.ecr_repo_name
  source_path     = "${path.module}/../../onboarding_Ariel/get_intro/"
  triggers        = { dir_sha = local.dir_sha }
}
