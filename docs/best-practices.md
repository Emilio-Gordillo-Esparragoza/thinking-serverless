# Best Practices: Serverless Architecture, Security & Avoiding Pitfalls

A practical guide to building serverless systems correctly. We cover security, cost optimization, avoiding over-engineering, and when simpler is better.

---

## Table of Contents

1. [Security Best Practices](#security-best-practices)
2. [IAM & Permissions](#iam--permissions)
3. [Cost Optimization](#cost-optimization)
4. [Avoiding Over-Engineering](#avoiding-over-engineering)
5. [When to Use Monolith vs Distributed](#when-to-use-monolith-vs-distributed)
6. [Common Pitfalls](#common-pitfalls)
7. [Production Readiness Checklist](#production-readiness-checklist)

---

## Security Best Practices

### 1. Never Use Resource: `*`

**Wrong:**

```json
{
  "Effect": "Allow",
  "Action": "s3:*",
  "Resource": "*"
}
```

This policy allows reading, deleting, and modifying **any** S3 bucket in your account. If your Lambda is compromised, attackers get full S3 access.

**Correct:**

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject",
    "s3:PutObject"
  ],
  "Resource": "arn:aws:s3:::my-app-bucket-prod/transactions/*"
}
```

This allows **only** reading and writing objects under `my-app-bucket-prod/transactions/`. Nothing else.

---

### 2. Never Open SSH (Port 22) to All Traffic

**Wrong:**

```
Type: SSH
Protocol: TCP
Port Range: 22
Source: 0.0.0.0/0   ← entire internet
```

**Correct:**

```
Type: SSH
Protocol: TCP
Port Range: 22
Source: 10.0.1.0/24       ← your VPC subnet only
  OR
Source: 203.0.113.45/32   ← your specific IP only
```

---

### 3. Never Open Database Ports to All Traffic

**Wrong:**

```
Type: MySQL/Aurora
Protocol: TCP
Port Range: 3306
Source: 0.0.0.0/0   ← entire internet
```

**Correct:**

```
Type: MySQL/Aurora
Protocol: TCP
Port Range: 3306
Source: 10.0.0.0/16   ← your VPC only
```

Databases should **never** be accessible from the internet.

---

### 4. Use Secrets Manager, Not Hardcoded Secrets

**Wrong:**

```python
# lambda_function.py

DB_PASSWORD = "super-secret-password-12345"
API_KEY = "sk-abc123def456"

def lambda_handler(event, context):
    conn = connect(password=DB_PASSWORD)
```

If this code is in GitHub, everyone sees your secrets.

**Correct:**

```python
# lambda_function.py

import boto3
import json

secrets_client = boto3.client('secretsmanager')

def get_db_password():
    response = secrets_client.get_secret_value(SecretId='prod/db/password')
    return json.loads(response['SecretString'])['password']

def lambda_handler(event, context):
    password = get_db_password()
    conn = connect(password=password)
```

Benefits: secrets stored encrypted, can rotate without redeploying, full audit trail, no sensitive data in git.

---

### 5. Enable Encryption at Rest and in Transit

**Wrong (DynamoDB):**

```hcl
resource "aws_dynamodb_table" "users" {
  name = "users"
  # No encryption specified — data readable by anyone with disk access
}
```

**Correct:**

```hcl
resource "aws_dynamodb_table" "users" {
  name = "users"

  sse_specification {
    enabled        = true
    sse_type       = "KMS"
    kms_master_arn = aws_kms_key.dynamodb.arn
  }
}
```

**Wrong (RDS):**

```hcl
resource "aws_db_instance" "postgres" {
  identifier        = "mydb"
  engine            = "postgres"
  allocated_storage = 20
  # stored unencrypted
}
```

**Correct:**

```hcl
resource "aws_db_instance" "postgres" {
  identifier        = "mydb"
  engine            = "postgres"
  allocated_storage = 20
  storage_encrypted = true
  kms_key_id        = aws_kms_key.rds.arn
}
```

---

### 6. Use VPC for Database Access

**Wrong:**

```
Lambda (public VPC) → RDS endpoint: mydb.abc123.us-east-1.rds.amazonaws.com
Database endpoint is publicly routable.
```

**Correct:**

```
Lambda (private subnet) → RDS (private subnet, no internet gateway)
Database has NO public endpoint. Attacker cannot reach it from the internet.
```

---

### 7. Enable Logging & Monitoring

**Wrong:**

```python
# No CloudWatch logs configured
# No X-Ray tracing
# No CloudTrail auditing
# If something goes wrong, you have no idea what happened.
```

**Correct:**

```python
# CloudWatch structured logging
logger.info(f"Processing transaction {transaction_id}")
logger.error(f"Error: {error_message}")

# X-Ray tracing
@xray_recorder.capture('process_transaction')
def process_transaction(event):
    ...
```

```hcl
# CloudWatch Alarms — alert if:
# - Lambda error rate > 1%
# - DynamoDB throttled
# - Unauthorized API calls detected
```

---

## IAM & Permissions

### Principle of Least Privilege

Grant **minimum** permissions needed. Nothing more.

**Wrong:**

```json
{
  "Effect": "Allow",
  "Action": "*",
  "Resource": "*"
}
```

Lambda can do anything to anything.

**Correct:**

```json
{
  "Effect": "Allow",
  "Action": [
    "sqs:ReceiveMessage",
    "sqs:DeleteMessage",
    "sqs:GetQueueAttributes"
  ],
  "Resource": "arn:aws:sqs:us-east-1:123456789012:transactions-queue"
},
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:GetItem",
    "dynamodb:PutItem"
  ],
  "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/Ledger"
}
```

Lambda can **only** read/delete from `transactions-queue` and get/put items in `Ledger`.

---

### Use Separate Roles per Function

**Wrong:**

```
# All Lambdas share one role
LambdaRole:
  - Can access all S3 buckets
  - Can access all DynamoDB tables
  - Can delete all SQS queues
  - Can invoke all other Lambdas

If one Lambda is compromised, attacker can do everything.
```

**Correct:**

```
ComplianceCheckRole:   → compliance SQS queue + idempotency table
FraudDetectionRole:    → fraud SQS queue + fraud DynamoDB table
LedgerUpdateRole:      → ledger SQS FIFO queue + ledger DynamoDB table

If one Lambda is compromised, attacker has access to ONLY that Lambda's resources.
```

---

### Use Resource-Based Policies for Cross-Account Access

**Account B (resource owner):**

```json
{
  "Effect": "Allow",
  "Principal": {
    "AWS": "arn:aws:iam::111111111111:role/LambdaRole"
  },
  "Action": "dynamodb:GetItem",
  "Resource": "arn:aws:dynamodb:us-east-1:222222222222:table/CrossAccountData"
}
```

**Account A (consumer):**

```json
{
  "Effect": "Allow",
  "Action": "dynamodb:GetItem",
  "Resource": "arn:aws:dynamodb:us-east-1:222222222222:table/CrossAccountData"
}
```

Lambda in Account A can read from DynamoDB in Account B — and that's all.

---

## Cost Optimization

### 1. Use On-Demand Billing for Unpredictable Workloads

**Wrong (DynamoDB provisioned):**

```hcl
resource "aws_dynamodb_table" "transactions" {
  billing_mode       = "PROVISIONED"
  read_capacity_units  = 100
  write_capacity_units = 100
  # You pay for 100 RCU/WCU whether you use them or not.
}
```

**Correct:**

```hcl
resource "aws_dynamodb_table" "transactions" {
  billing_mode = "PAY_PER_REQUEST"
  # Pay only for what you use. Traffic spikes? Auto-scales.
}
```

**Cost comparison:**

| Scenario | Provisioned | On-Demand |
|---|---|---|
| 10M reads/month | $47.50 (fixed) | ~$2.50 |
| 100M reads/month | $47.50 (fixed) | ~$25.00 |
| 1B reads/month | Calculate | Provisioned may win |

---

### 2. Delete Unused Resources

**Wrong:**

```hcl
resource "aws_instance" "old_dev_server" {
  instance_type = "t3.large"
  # Still charged even though nobody uses it
}
```

**Correct:**

```hcl
resource "aws_instance" "dev_server" {
  tags = {
    Name       = "dev-server"
    Expiration = "2024-02-01"
  }
}
```

```python
# Lambda to auto-delete expired resources
def cleanup_expired_resources():
    today = datetime.now()
    for instance in ec2.describe_instances():
        expiration = instance['Tags'].get('Expiration')
        if expiration < today:
            ec2.terminate_instances(InstanceIds=[instance['InstanceId']])
```

---

### 3. Use Reserved Capacity for Predictable Workloads

```
50 concurrent Lambda executions (always-on):

On-demand:   50 GB-sec/sec × $0.0000167 × 86400 × 30 ≈ $2,160/month
Reserved:    50 GB × 730 hours × $0.015             ≈ $547/month

Savings: ~$1,600/month (75%)
```

---

### 4. Use SQS FIFO Only When You Need Ordering

**Wrong:**

```hcl
# All events use FIFO — throughput capped at 3,000 msg/sec per partition key
resource "aws_sqs_queue" "all_events" {
  fifo_queue = true
}
```

**Correct:**

```hcl
# Standard queue for events that don't need ordering — 300K msg/sec
resource "aws_sqs_queue" "async_tasks" {
  fifo_queue = false
}

# FIFO only for ledger transactions where ordering matters
resource "aws_sqs_queue" "ledger_updates" {
  fifo_queue = true
}
```

---

## Avoiding Over-Engineering

### 1. Start with a Monolith

**Wrong (premature microservices for a simple blog):**

```
Architecture:
  - API Gateway
  - 5 separate Lambda functions (auth, posts, comments, users, analytics)
  - 5 DynamoDB tables
  - EventBridge for inter-service communication
  - 15+ IAM roles
  - X-Ray tracing everywhere
  - Multi-region failover

Result: 3 months to build, $200/month, nobody uses it.
```

**Correct:**

```
Architecture:
  - API Gateway
  - 1 Lambda function
  - 1 DynamoDB table (single-table design)
  - 1 IAM role
  - CloudWatch Logs

Result: 2 weeks to build, $5/month, easy to maintain.
```

---

### 2. Don't Use Distributed Systems Until You Need Them

```
Single Lambda, 100 requests/month, 200ms each.

Developer thinks: "This could fail! I need resilience!"
Adds: SQS queue, 3 consumers, idempotency store, DLQ, monitoring.

Complexity: 10×    Maintenance: 10×    Cost: 10×    Benefit: 0
```

Start simple. Monitor. Add complexity only when a measured problem demands it.

---

### 3. One Database, Not Ten

**Wrong:**

```
Compliance service → PostgreSQL
Fraud service      → MongoDB
Ledger service     → DynamoDB

How do you query across them? Three schemas. Three backups. Three teams.
```

**Correct (DynamoDB single-table design):**

| PK | SK | Data |
|---|---|---|
| `TXN#TX-001` | `COMPLIANCE` | `{status, amlScore, …}` |
| `TXN#TX-001` | `FRAUD` | `{status, fraudScore, …}` |
| `TXN#TX-001` | `LEDGER` | `{status, amount, …}` |
| `TXN#TX-002` | `COMPLIANCE` | `{status, amlScore, …}` |

One table. One schema. One backup. Query all data in one request.

---

### 4. Don't Over-Monitor

**Wrong:**

```
50 different metrics for a 1-user side project.
Result: 2 hours/week maintaining dashboards, 0 actual incidents detected.
```

**Correct:**

```
For a 1-user side project, 3 metrics is enough:
- Lambda error rate > 5%? Alert.
- API latency > 5 seconds? Something's wrong.
- DynamoDB throttles > 0? Alert.
```

---

## When to Use Monolith vs Distributed

### Monolith If:

| Signal | Threshold |
|---|---|
| Team size | 1–5 engineers |
| User base | < 100K users |
| Traffic | < 1,000 req/sec |
| Business requirements | Changing frequently |
| Deployment cadence | < 10 times/day |
| Failure tolerance | All-or-nothing is acceptable |

**Example:**

```python
def lambda_handler(event, context):
    path = event['path']
    if path == '/api/transactions':
        return handle_transactions(event)
    elif path == '/api/compliance':
        return handle_compliance(event)
    elif path == '/api/fraud':
        return handle_fraud(event)
    elif path == '/api/ledger':
        return handle_ledger(event)
```

1 Lambda. 1 button to deploy. 2-minute rollback.

---

### Distributed If:

| Signal | Threshold |
|---|---|
| Team size | 10+ engineers |
| User base | 100K+ users |
| Traffic | > 1,000 req/sec |
| Business requirements | Stable, well-defined |
| Deployment cadence | > 10 times/day |
| Failure tolerance | Partial failures acceptable |

**Example:**

```
API Gateway → Router Lambda
              ├─ /api/transactions → Orchestration Lambda
              ├─ /api/compliance  → Compliance Lambda
              ├─ /api/fraud       → Fraud Lambda
              └─ /api/ledger      → Ledger Lambda
```

Each domain: separate code, separate Lambda, separate DynamoDB, independent deployment.

---

## Common Pitfalls

### Pitfall 1: Using CloudFormation for Everything

**Wrong:** 10,000 lines of YAML. One typo — entire stack fails.

**Correct:**

```hcl
# Terraform for infrastructure
resource "aws_dynamodb_table" "transactions" { ... }
resource "aws_lambda_function" "processor" { ... }
```

```python
# SAM or raw Python for Lambda code
def lambda_handler(event, context): ...
```

---

### Pitfall 2: Not Using Dead-Letter Queues

**Wrong:**

```
EventBridge → SQS → Lambda
If Lambda fails 3 times, message is deleted. Lost forever.
```

**Correct:**

```
EventBridge → SQS → Lambda
                ↓
              DLQ (on failure)
```

```hcl
resource "aws_sqs_queue" "main" {
  name = "transactions-queue"
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue" "dlq" {
  name                      = "transactions-queue-dlq"
  message_retention_seconds = 1209600  # 14 days
}
```

---

### Pitfall 3: Not Testing Locally

**Wrong:** Write Lambda → deploy to AWS → test in production. 30-minute cycles, $100 in failed tests.

**Correct:**

```bash
# LocalStack — fake AWS, free, instant
docker run -d -p 4566:4566 localstack/localstack

# Run tests against LocalStack
pytest tests/test_lambda.py

# Deploy to AWS only after tests pass
```

---

### Pitfall 4: Not Using Environment Variables

**Wrong:**

```python
DB_HOST  = "mydb.abc123.us-east-1.rds.amazonaws.com"
API_KEY  = "sk-prod-12345"
```

**Correct:**

```python
import os

DB_HOST  = os.getenv('DB_HOST')
API_KEY  = os.getenv('API_KEY')
```

```hcl
resource "aws_lambda_function" "processor" {
  environment {
    variables = {
      DB_HOST  = aws_db_instance.prod.endpoint
      API_KEY  = aws_secretsmanager_secret.api_key.id
    }
  }
}
```

Dev and prod Lambda are identical — only environment variables differ.

---

### Pitfall 5: Trying to Handle Every Edge Case

**Wrong:** 500-line Lambda handling null values, retries, throttles, schema versions, fallback caches. Impossible to test.

**Correct:**

```python
def lambda_handler(event, context):
    # Fail fast on invalid input
    if not event.get('transactionId'):
        raise ValueError("Missing transactionId")
    if event['amount'] <= 0:
        raise ValueError("Amount must be positive")

    # Do the work
    result = process_transaction(event)
    return result

# Let AWS handle the rest:
# - Retries      (SQS: 3 by default)
# - Timeouts     (Lambda: configurable)
# - Throttles    (SQS: automatic backoff)
# - Failures     (DLQ: captured for inspection)
```

Code is 10× simpler. 10× more reliable.

---

## Production Readiness Checklist

### Security

- [ ] No hardcoded secrets (use Secrets Manager)
- [ ] No `Resource: *` in IAM policies
- [ ] No `0.0.0.0/0` in Security Groups
- [ ] Database encrypted at rest (KMS)
- [ ] Data encrypted in transit (TLS)
- [ ] VPC configured (private subnets for databases)
- [ ] API Gateway has request validation enabled
- [ ] CloudTrail logging enabled

### Resilience

- [ ] Dead-Letter Queues configured
- [ ] Retry policies defined (exponential backoff)
- [ ] Timeout values set (Lambda, database connections)
- [ ] Load testing passed (expected throughput)

### Observability

- [ ] CloudWatch Logs enabled with structured (JSON) logging
- [ ] Key metrics defined (latency, error rate, throughput)
- [ ] CloudWatch Alarms configured
- [ ] X-Ray tracing enabled
- [ ] Runbooks written for common failure scenarios

### Cost

- [ ] Reserved capacity calculated (if using provisioned)
- [ ] Unused resources identified and deleted
- [ ] Cost alerts configured (warn if exceeds budget)
- [ ] Scaling limits set (prevent runaway costs)

### Operations

- [ ] Disaster recovery plan documented
- [ ] Backup strategy defined
- [ ] Rollback procedure tested

### Testing

- [ ] Unit tests written (> 80% code coverage)
- [ ] Integration tests passing (with LocalStack)
- [ ] Load tests passing

---

## Quick Decision Trees

### Should I Use Microservices?

```
Team size > 10?
├─ YES → Maybe, only if teams are truly autonomous
└─ NO  → Use monolith

Traffic > 10K req/sec?
├─ YES → Maybe, if certain domains need independent scaling
└─ NO  → Use monolith

Deployment cadence > 20/day?
├─ YES → Maybe, if different teams deploy independently
└─ NO  → Use monolith

All YES? → Microservices might help. Otherwise: monolith.
```

### Should I Use FIFO Queues?

```
Do messages need strict ordering?
├─ YES → FIFO queue
└─ NO  → Standard queue (cheaper, 100× faster)

Examples:
  Ledger updates   → FIFO (must process in order per account)
  Email alerts     → Standard (order doesn't matter)
```

### Should I Use Provisioned DynamoDB Capacity?

```
Is traffic predictable AND consistent?
├─ YES → Calculate if provisioned is cheaper
└─ NO  → On-demand (simpler, auto-scales)
```

### Should I Enable Lambda Provisioned Concurrency?

```
Can you tolerate cold starts (~100–500ms)?
├─ YES → Let it scale up (cheaper)
└─ NO  → Enable provisioned concurrency (keep containers warm)
```

---

## Summary: The 80/20 Rule

80% of projects need:

| Component | Choice |
|---|---|
| Compute | 1 Lambda monolith |
| Database | 1 DynamoDB table (single-table design) |
| Storage | 1 S3 bucket (if storing files) |
| API | API Gateway |
| Monitoring | Basic CloudWatch |

**Cost:** $20–50/month. **Complexity:** Low. **Maintenance:** Minimal.

Only reach for advanced patterns (EventBridge, FIFO, multi-region) when:
- You've **measured** a specific problem (not guessed)
- A simple solution won't fix it
- ROI justifies the added complexity

Start simple. Add complexity only when needed.
