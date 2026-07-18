variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

resource "aws_iam_role" "new_order" {
  name = "new-order-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_execution" {
  name   = "lambda-execution-policy"
  role   = aws_iam_role.new_order.id
  policy = file("${path.module}/../../../../shared/iam-policies/lambda_execution_policy.json")
}

resource "aws_lambda_function" "new_order" {
  filename         = "${path.module}/../../src/new_order/lambda_function.py"
  function_name    = "new-order-${var.environment}"
  role             = aws_iam_role.new_order.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  source_code_hash = filebase64sha256("${path.module}/../../src/new_order/lambda_function.py")
}

resource "aws_api_gateway_rest_api" "orders" {
  name        = "orders-api-${var.environment}"
  description = "Synchronous order processing API"
}

resource "aws_api_gateway_resource" "orders" {
  rest_api_id = aws_api_gateway_rest_api.orders.id
  parent_id   = aws_api_gateway_rest_api.orders.root_resource_id
  path_part   = "orders"
}

resource "aws_api_gateway_method" "post_order" {
  rest_api_id   = aws_api_gateway_rest_api.orders.id
  resource_id   = aws_api_gateway_resource.orders.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda" {
  rest_api_id             = aws_api_gateway_rest_api.orders.id
  resource_id             = aws_api_gateway_resource.orders.id
  http_method             = aws_api_gateway_method.post_order.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.new_order.invoke_arn
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.new_order.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.orders.execution_arn}/*/*/*"
}

resource "aws_api_gateway_deployment" "orders" {
  depends_on  = [aws_api_gateway_integration.lambda]
  rest_api_id = aws_api_gateway_rest_api.orders.id

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "orders" {
  deployment_id = aws_api_gateway_deployment.orders.id
  rest_api_id   = aws_api_gateway_rest_api.orders.id
  stage_name    = var.environment
}

output "api_endpoint" {
  value = "${aws_api_gateway_rest_api.orders.execution_arn}/${var.environment}/POST/orders"
}
