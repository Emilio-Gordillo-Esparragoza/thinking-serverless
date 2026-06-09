variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

resource "aws_sqs_queue" "compliance" {
  name = "compliance-queue-${var.environment}"
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.compliance_dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue" "compliance_dlq" {
  name = "compliance-dlq-${var.environment}"
}

resource "aws_sqs_queue_policy" "eventbridge_write" {
  queue_url = aws_sqs_queue.compliance.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.compliance.arn
      }
    ]
  })
}

resource "aws_iam_role" "compliance_check" {
  name = "compliance-check-role-${var.environment}"

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

resource "aws_iam_role_policy" "sqs_consumer" {
  name   = "sqs-consumer-policy"
  role   = aws_iam_role.compliance_check.id
  policy = file("${path.module}/../../../../../shared/iam-policies/sqs_consumer_policy.json")
}

resource "aws_iam_role_policy" "lambda_execution" {
  name   = "lambda-execution-policy"
  role   = aws_iam_role.compliance_check.id
  policy = file("${path.module}/../../../../../shared/iam-policies/lambda_execution_policy.json")
}

resource "aws_lambda_function" "compliance_check" {
  filename         = "${path.module}/../../src/compliance_check/lambda_function.py"
  function_name    = "compliance-check-${var.environment}"
  role             = aws_iam_role.compliance_check.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  source_code_hash = filebase64sha256("${path.module}/../../src/compliance_check/lambda_function.py")
}

resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.compliance.arn
  function_name    = aws_lambda_function.compliance_check.arn
  batch_size       = 10
}

output "compliance_queue_arn" {
  value = aws_sqs_queue.compliance.arn
}

output "compliance_queue_url" {
  value = aws_sqs_queue.compliance.id
}
