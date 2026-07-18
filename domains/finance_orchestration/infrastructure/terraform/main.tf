variable "compliance_queue_arn" {
  description = "ARN of the compliance SQS queue"
  type        = string
}

variable "fraud_queue_arn" {
  description = "ARN of the fraud detection SQS queue"
  type        = string
}

variable "ledger_queue_arn" {
  description = "ARN of the ledger update SQS queue"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

resource "aws_schemas_registry" "main" {
  name = "finance-events-registry"
}

resource "aws_schemas_schema" "transaction_event" {
  name          = "TransactionEvent"
  registry_name = aws_schemas_registry.main.name
  type          = "OpenApi3"
  content = jsonencode({
    openapi = "3.0.0"
    info = {
      title   = "TransactionEvent"
      version = "1.0.0"
    }
    components = {
      schemas = {
        TransactionEvent = jsondecode(file("${path.module}/../../../../shared/event-schemas/TransactionEvent.json"))
      }
    }
  })
}

resource "aws_cloudwatch_event_bus" "finance" {
  name = "finance-events"
}

resource "aws_cloudwatch_event_rule" "route_to_compliance" {
  name           = "route-to-compliance"
  event_bus_name = aws_cloudwatch_event_bus.finance.name
  event_pattern = jsonencode({
    source      = ["finance.orchestration"]
    detail-type = ["TransactionProcessed"]
  })
}

resource "aws_cloudwatch_event_target" "compliance" {
  rule           = aws_cloudwatch_event_rule.route_to_compliance.name
  event_bus_name = aws_cloudwatch_event_bus.finance.name
  arn            = var.compliance_queue_arn
}

resource "aws_cloudwatch_event_rule" "route_to_fraud" {
  name           = "route-to-fraud"
  event_bus_name = aws_cloudwatch_event_bus.finance.name
  event_pattern = jsonencode({
    source      = ["finance.orchestration"]
    detail-type = ["TransactionProcessed"]
  })
}

resource "aws_cloudwatch_event_target" "fraud" {
  rule           = aws_cloudwatch_event_rule.route_to_fraud.name
  event_bus_name = aws_cloudwatch_event_bus.finance.name
  arn            = var.fraud_queue_arn
}

resource "aws_cloudwatch_event_rule" "route_to_ledger" {
  name           = "route-to-ledger"
  event_bus_name = aws_cloudwatch_event_bus.finance.name
  event_pattern = jsonencode({
    source      = ["finance.orchestration"]
    detail-type = ["TransactionProcessed"]
  })
}

resource "aws_cloudwatch_event_target" "ledger" {
  rule           = aws_cloudwatch_event_rule.route_to_ledger.name
  event_bus_name = aws_cloudwatch_event_bus.finance.name
  arn            = var.ledger_queue_arn
}

resource "aws_sqs_queue" "process_transaction_dlq" {
  name = "process-transaction-dlq-${var.environment}"
}

resource "aws_iam_role" "process_transaction" {
  name = "process-transaction-role-${var.environment}"

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

resource "aws_iam_role_policy" "eventbridge_put" {
  name   = "eventbridge-put-policy"
  role   = aws_iam_role.process_transaction.id
  policy = file("${path.module}/../../../../shared/iam-policies/eventbridge_put_policy.json")
}

resource "aws_iam_role_policy" "lambda_execution" {
  name   = "lambda-execution-policy"
  role   = aws_iam_role.process_transaction.id
  policy = file("${path.module}/../../../../shared/iam-policies/lambda_execution_policy.json")
}

resource "aws_lambda_function" "process_transaction" {
  filename         = "${path.module}/../../src/process_transaction/lambda_function.py"
  function_name    = "process-transaction-${var.environment}"
  role             = aws_iam_role.process_transaction.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  source_code_hash = filebase64sha256("${path.module}/../../src/process_transaction/lambda_function.py")

  environment {
    variables = {
      EVENT_BUS_NAME = aws_cloudwatch_event_bus.finance.name
    }
  }
}

output "event_bus_name" {
  value = aws_cloudwatch_event_bus.finance.name
}

output "event_bus_arn" {
  value = aws_cloudwatch_event_bus.finance.arn
}
