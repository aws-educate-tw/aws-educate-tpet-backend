####################################
####################################
####################################
# Public bucket ####################
####################################
####################################
####################################

resource "aws_s3_bucket" "aws_educate_tpet_storage" {
  bucket = "${var.environment}-aws-educate-tpet-storage"

  tags = {
    Name        = "${var.environment}-aws-educate-tpet-storage"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_public_access_block" "public_access_block" {
  bucket = aws_s3_bucket.aws_educate_tpet_storage.bucket

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}
resource "aws_s3_bucket_policy" "aws_educate_tpet_storage_policy" {
  bucket = aws_s3_bucket.aws_educate_tpet_storage.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Principal = "*",
        Action    = "s3:GetObject",
        Resource  = "${aws_s3_bucket.aws_educate_tpet_storage.arn}/*"
      }
    ]
  })
}
resource "aws_s3_bucket_cors_configuration" "aws_educate_tpet_storage_cors" {
  bucket = aws_s3_bucket.aws_educate_tpet_storage.id

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

resource "aws_s3_bucket" "aws_educate_tpet_private_storage" {
  bucket = "${var.environment}-aws-educate-tpet-private-storage"

  tags = {
    Name        = "${var.environment}-aws-educate-tpet-private-storage"
    Environment = var.environment
  }
}
