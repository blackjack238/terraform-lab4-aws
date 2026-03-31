variable "api_name" {
  type = string
}

variable "lambda_invoke_arn" {
  type = string
}

variable "lambda_function_name" {
  type = string
}

# 1. Створення HTTP API
resource "aws_apigatewayv2_api" "http_api" {
  name          = var.api_name
  protocol_type = "HTTP"
}

# 2. Lambda proxy integration
resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  integration_uri        = var.lambda_invoke_arn
  payload_format_version = "2.0"
}

# 3. Маршрути
resource "aws_apigatewayv2_route" "post_tasks" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /tasks"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "get_tasks" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /tasks"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "put_task" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "PUT /tasks/{id}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "post_prioritize_task" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /tasks/{id}/prioritize"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# 4. Stage $default
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
}

# 5. Дозвіл API Gateway викликати Lambda
resource "aws_lambda_permission" "api_gw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}

output "api_endpoint" {
  value = aws_apigatewayv2_api.http_api.api_endpoint
}

output "api_id" {
  value = aws_apigatewayv2_api.http_api.id
}