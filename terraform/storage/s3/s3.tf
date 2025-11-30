####################################
####################################
####################################
# Public bucket ####################
####################################
####################################
####################################

resource "aws_s3_bucket" "aws_educate_tpet_bucket" {
  bucket = "${var.environment}-aws-educate-tpet-bucket"

  tags = {
    Name        = "${var.environment}-aws-educate-tpet-bucket"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_public_access_block" "public_access_block" {
  bucket = aws_s3_bucket.aws_educate_tpet_bucket.bucket

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}
resource "aws_s3_bucket_policy" "aws_educate_tpet_bucket_policy" {
  bucket = aws_s3_bucket.aws_educate_tpet_bucket.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Principal = "*",
        Action    = "s3:GetObject",
        Resource  = "${aws_s3_bucket.aws_educate_tpet_bucket.arn}/*"
      }
    ]
  })
}
resource "aws_s3_bucket_cors_configuration" "aws_educate_tpet_bucket_cors" {
  bucket = aws_s3_bucket.aws_educate_tpet_bucket.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET"]
    allowed_origins = var.cors_allowed_origins
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

####################################
####################################
####################################
# Private bucket ####################
####################################
####################################
####################################

resource "aws_s3_bucket" "aws_educate_tpet_private_bucket" {
  bucket = "${var.environment}-aws-educate-tpet-private-bucket"

  tags = {
    Name        = "${var.environment}-aws-educate-tpet-private-bucket"
    Environment = var.environment
  }
}
