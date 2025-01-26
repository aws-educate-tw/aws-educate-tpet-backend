
module "lambda-warmer" {
  source  = "aws-educate-tw/tag-based-lambda-warmer/aws"
  version = "0.2.0"

  aws_region  = var.aws_region
  environment = var.environment
}
