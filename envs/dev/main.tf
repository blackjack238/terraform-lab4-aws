provider "aws" {
  region = "eu-central-1"
}

locals {
  prefix = "kaparov-oleksii-04"

  # Для S3 бакета потрібна глобально унікальна назва
  audit_bucket_name = "kaparov-oleksii-04-audit-2026"
}

# DynamoDB для задач
module "database" {
  source     = "../../modules/dynamodb"
  table_name = "${local.prefix}-tasks"
}

# S3 для audit-log
module "audit_logs" {
  source      = "../../modules/s3"
  bucket_name = local.audit_bucket_name
}

# Lambda
module "backend" {
  source              = "../../modules/lambda"
  function_name       = "${local.prefix}-api-handler"
  source_file         = "${path.root}/../../src/app.py"
  dynamodb_table_arn  = module.database.table_arn
  dynamodb_table_name = module.database.table_name
  audit_bucket_name   = module.audit_logs.bucket_name

  # якщо у модулі DynamoDB є GSI status-index
  dynamodb_index_arn = "${module.database.table_arn}/index/status-index"
}

# API Gateway
module "api" {
  source               = "../../modules/api_gateway"
  api_name             = "${local.prefix}-http-api"
  lambda_invoke_arn    = module.backend.invoke_arn
  lambda_function_name = module.backend.function_name
}

output "api_url" {
  value = module.api.api_endpoint
}

output "dynamodb_table_name" {
  value = module.database.table_name
}

output "audit_bucket_name" {
  value = module.audit_logs.bucket_name
}

output "lambda_function_name" {
  value = module.backend.function_name
}