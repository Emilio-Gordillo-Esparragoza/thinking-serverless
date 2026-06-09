variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

resource "aws_sqs_queue" "fraud" {
  name = "fraud-queue-${var.environment}"
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.fraud_dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue" "fraud_dlq" {
  name = "fraud-dlq-${var.environment}"
}

resource "aws_sqs_queue_policy" "eventbridge_write" {
  queue_url = aws_sqs_queue.fraud.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.fraud.arn
      }
    ]
  })
}

resource "aws_iam_role" "fraud_detection" {
  name = "fraud-detection-role-${var.environment}"

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
  role   = aws_iam_role.fraud_detection.id
  policy = file("${path.module}/../../../../../shared/iam-policies/sqs_consumer_policy.json")
}

resource "aws_iam_role_policy" "lambda_execution" {
  name   = "lambda-execution-policy"
  role   = aws_iam_role.fraud_detection.id
  policy = file("${path.module}/../../../../../shared/iam-policies/lambda_execution_policy.json")
}

resource "aws_lambda_function" "fraud_detection" {
  filename         = "${path.module}/../../src/fraud_detection/lambda_function.py"
  function_name    = "fraud-detection-${var.environment}"
  role             = aws_iam_role.fraud_detection.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  source_code_hash = filebase64sha256("${path.module}/../../src/fraud_detection/lambda_function.py")
}

resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.fraud.arn
  function_name    = aws_lambda_function.fraud_detection.arn
  batch_size       = 10
}

output "fraud_queue_arn" {
  value = aws_sqs_queue.fraud.arn
}

output "fraud_queue_url" {
  value = aws_sqs_queue.fraud.id
}
