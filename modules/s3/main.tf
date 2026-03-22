variable "bucket_name" {
  description = "Globally unique S3 bucket name for audit logs"
  type        = string
}

resource "aws_s3_bucket" "audit" {
  bucket = var.bucket_name
   force_destroy = true
}

output "bucket_name" {
  value = aws_s3_bucket.audit.bucket
}

output "bucket_arn" {
  value = aws_s3_bucket.audit.arn
}

