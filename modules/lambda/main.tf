variable "function_name" {
  type = string
}

variable "source_file" {
  type = string
}

variable "dynamodb_table_arn" {
  type = string
}

variable "dynamodb_table_name" {
  type = string
}

variable "audit_bucket_name" {
  type = string
}

# Якщо використовуєш GSI для status, можна передати ARN індексів
variable "dynamodb_index_arn" {
  type    = string
  default = null
}

# Автоматичне створення ZIP-архіву з Python-коду
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = var.source_file
  output_path = "${path.module}/app.zip"
}

# IAM role для Lambda
resource "aws_iam_role" "lambda_exec" {
  name = "${var.function_name}_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Базові CloudWatch logs для Lambda
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Мінімально необхідний доступ до DynamoDB
resource "aws_iam_role_policy" "dynamodb_access" {
  name = "${var.function_name}_dynamodb_access"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:GetItem",
          "dynamodb:Scan",
          "dynamodb:Query"
        ]
        Resource = compact([
          var.dynamodb_table_arn,
          var.dynamodb_index_arn
        ])
      }
    ]
  })
}

# Доступ до запису audit-log у S3
resource "aws_iam_role_policy" "s3_audit_access" {
  name = "${var.function_name}_s3_audit_access"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject"
        ]
        Resource = "arn:aws:s3:::${var.audit_bucket_name}/audit/*"
      }
    ]
  })
}

# Lambda function
resource "aws_lambda_function" "api_handler" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = var.function_name
  role             = aws_iam_role.lambda_exec.arn
  handler          = "app.handler"
  runtime          = "python3.12"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 10

  environment {
    variables = {
      TABLE_NAME   = var.dynamodb_table_name
      AUDIT_BUCKET = var.audit_bucket_name
    }
  }
}

output "invoke_arn" {
  value = aws_lambda_function.api_handler.invoke_arn
}

output "function_name" {
  value = aws_lambda_function.api_handler.function_name
}

output "lambda_arn" {
  value = aws_lambda_function.api_handler.arn
}