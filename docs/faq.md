# FAQ: Serverless Architecture & AWS Services

A practical guide to understanding AWS serverless services, their purposes, and when to use them. We translate AWS jargon into universally understood concepts and compare them to standard tools like Kafka, RabbitMQ, and traditional architectures.

---

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [AWS Messaging Services](#aws-messaging-services)
3. [SQS vs SNS vs EventBridge](#sqs-vs-sns-vs-eventbridge)
4. [Real-World Decision Trees](#real-world-decision-trees)
5. [Comparison with Standard Tools](#comparison-with-standard-tools)
6. [Lambda & Compute](#lambda--compute)
7. [Data Storage](#data-storage)
8. [Troubleshooting](#troubleshooting)

---

## Core Concepts

### What is Serverless?

Serverless means you write functions that run in response to events. You don't manage servers, scaling, or infrastructure. You pay only for the compute time your code actually uses.

> Think of it like hiring a contractor for a specific job instead of a full-time employee. You pay per task, not salary.

| Model | Cost | Management |
|---|---|---|
| EC2 (traditional) | $100–$1,000+/month (always running) | You manage servers, scaling, patches |
| Lambda (serverless) | ~$0.0000002/execution | AWS manages everything |

---

### What is an Event?

An event is something that happens in your system that triggers a function:

- A user uploads a file to S3
- A message arrives in an SQS queue
- A scheduled time (cron) passes
- An HTTP request hits API Gateway
- A DynamoDB stream emits a change

---

### What is a Message Broker?

A message broker is a middleman that receives messages from producers (senders) and delivers them to consumers (receivers). It decouples producers from consumers so they don't need to know about each other.

> Like a post office. The sender doesn't need to know the recipient; the post office routes the mail.

---

## AWS Messaging Services

### SQS (Simple Queue Service)

A message queue — a durable inbox that stores messages until a consumer processes them.

**Mental model:**

```
Producer → [SQS Queue] → Consumer
            (holds messages until pulled)
```

**Key characteristics:**

| Property | Behavior |
|---|---|
| Delivery model | Pull-based (consumer polls) |
| Durability | Stores messages up to 14 days |
| Delivery guarantee | At-least-once (may duplicate) |
| Backpressure | Yes — queue fills up, consumers scale up |
| Ordering | Optional (FIFO queues) |

**Throughput:**

| Queue Type | Throughput |
|---|---|
| Standard | ~300,000 msg/sec per queue |
| FIFO | ~3,000 msg/sec per partition key |

**Cost:** $0.40 per million requests.

**When to use SQS:**

- Decoupling Lambda from Lambda
- Buffering spiky traffic
- Async task processing (email, image resizing, reports)
- Retry logic with automatic backoff
- Need to replay/reprocess messages

**Example flow:**

```
1. Lambda 1 receives photo upload
2. Puts message in SQS: "PhotoUploaded: photo123.jpg"
3. Lambda 2 polls SQS
4. Lambda 2 gets message, resizes the image
5. Lambda 2 deletes message (marks it done)
```

> SQS Standard ≈ RabbitMQ (at-least-once, pull-based)  
> SQS FIFO ≈ Kafka partition (ordered, exactly-once within partition)

---

### SNS (Simple Notification Service)

A pub/sub broker — one producer publishes to a topic, and all subscribers instantly receive a copy.

**Mental model:**

```
Producer → [SNS Topic] → Subscriber 1
                       → Subscriber 2
                       → Subscriber 3
            (fan-out, push-based)
```

**Key characteristics:**

| Property | Behavior |
|---|---|
| Delivery model | Push-based (SNS pushes to subscribers) |
| Durability | None — message lost if subscriber isn't listening |
| Fan-out | Yes — one publish triggers all subscribers simultaneously |
| Ordering | No FIFO available |
| Real-time | Near-instant |

**Throughput:** ~100,000 msg/sec.

**Cost:** $0.50 per million publish requests.

**When to use SNS:**

- Broadcasting announcements (all subscribers need it immediately)
- Mobile push notifications
- Email/SMS alerts
- Fan-out to always-on services

**Example flow:**

```
News headline published to SNS topic "NewsAlert"
→ All mobile apps:  push notification (instantly)
→ All email subs:   email (instantly)
→ Slack bot:        posts to #news (instantly)
(all happen in parallel)
```

> ⚠️ SNS doesn't store messages. If a subscriber is scaled down, it misses the message. Use SQS under SNS for durability.

---

### EventBridge

A smart event router — pattern matching, filtering, and fan-out on top of SNS/SQS.

**Mental model:**

```
Event Producer → [EventBridge Bus] → Rule 1: if pattern A → SQS
                                   → Rule 2: if pattern B → Lambda
                                   → Rule 3: if pattern C → SNS
                                    (intelligent fan-out)
```

**Key characteristics:**

| Property | Behavior |
|---|---|
| Pattern matching | Route based on event content (field values, types) |
| Built-in sources | AWS services, SaaS apps (Salesforce, Stripe), custom |
| Scheduled delivery | Cron-like scheduling built in |
| Schema registry | Validate event structure before routing |
| DLQ support | Failed events captured for inspection |

**Throughput:** ~100,000 events/sec.

**Cost:** $1.00 per million events published.

**When to use EventBridge:**

- Fan-out with intelligent routing (Payment events → one queue, Refund events → another)
- Integrating AWS services with SaaS
- Scheduled/delayed execution (replacing EC2 crons)
- Central event hub with audit trail

**Example flow:**

```json
// Event published to EventBridge
{
  "type": "TransactionCreated",
  "amount": 5000,
  "accountId": "acc-123"
}
```

```
EventBridge rules:
  Rule 1: IF amount > 1000  → Compliance SQS queue
  Rule 2: IF amount > 0     → Fraud SQS queue
  Rule 3: IF type matches   → Ledger SQS queue

Result: one event triggers three independent consumers
```

---

## SQS vs SNS vs EventBridge

### Feature Comparison

| Feature | SQS | SNS | EventBridge |
|---|---|---|---|
| Type | Queue (pull) | Pub/Sub (push) | Event router (push) |
| Storage | Yes (14 days) | No | Yes (for targets) |
| Delivery model | Pull-based | Push-based | Push-based |
| Multiple consumers | All drain the same queue | Each gets independent copy | Each target gets independent copy |
| Pattern matching | No | No | Yes |
| Ordering | FIFO available | No | FIFO available (limited) |
| Backpressure | Yes | No | Partial |
| Real-time | ~100ms | Instant | Instant |
| Cost per million | $0.40 | $0.50 | $1.00 |

### When to Choose Each

| Use case | Best fit | Why |
|---|---|---|
| Async task queue (image resize, email) | SQS | Durable, retries, backpressure |
| Mobile push notifications | SNS | Push-based, instant fan-out |
| Broadcast to many always-on services | SNS | Immediate, parallel delivery |
| Route events by content | EventBridge | Pattern matching on fields |
| Integrate AWS services with SaaS | EventBridge | 200+ built-in integrations |
| Scheduled/cron jobs | EventBridge | Native scheduler |
| Fan-out + durability | EventBridge + SQS | Smart routing + durable buffer |
| Strict message ordering | SQS FIFO | Per-partition ordering guarantee |

---

## Real-World Decision Trees

### Scenario 1: Processing User Uploads

Requirement: When a user uploads a file, resize images, extract metadata, and index for search. User should get immediate feedback.

**Decision flow:**

```
Do we need immediate response?  YES
└─ API Gateway → Lambda (sync) → return 202 Accepted immediately

Do we need durability?  YES
└─ Use SQS

Do multiple independent services need the file?  YES
└─ Use EventBridge + SQS (fan-out)
   Event: FileUploaded
   Rule 1 → SQS → Lambda (resize)
   Rule 2 → SQS → Lambda (metadata)
   Rule 3 → SQS → Lambda (search index)
```

**Result:**

```
User → API Gateway → Lambda 1 (validates) → 202 Accepted
                     └─ PutEvents → EventBridge
                                    ├─ SQS → Lambda 2 (resize)
                                    ├─ SQS → Lambda 3 (metadata)
                                    └─ SQS → Lambda 4 (search)
                                    (all 3 run in parallel)
```

---

### Scenario 2: Real-Time Stock Price Alerts

Requirement: When stock price changes, instantly notify all subscribed users via push, email, and SMS.

**Decision flow:**

```
Do we need real-time delivery?  YES → SNS
Do messages need to be stored?  NO  → SNS is sufficient
Do multiple subscribers need the same message?  YES → SNS topic
```

**Result:**

```
Stock service → SNS Topic (PriceAlert) → Mobile app (push)
                                       → Email service
                                       → SMS service
(all happen simultaneously, ~100ms)
```

---

### Scenario 3: Financial Transaction Processing

Requirement: Run compliance checks, fraud detection, and ledger updates. Each can fail independently, all failures must be retried and tracked.

**Decision flow:**

```
Do we need independent failure handling?   YES → no sync Lambda chaining
Do we need ordering for ledger?            YES → SQS FIFO
Do we need durable storage?                YES → SQS (not SNS)
Do we need smart routing?                  YES → EventBridge
Do we need to replay events?               YES → EventBridge + SQS
```

**Result:**

```
Transaction API
  → EventBridge
      ├─ Rule 1 → SQS Standard → Lambda (compliance)
      ├─ Rule 2 → SQS Standard → Lambda (fraud)
      └─ Rule 3 → SQS FIFO    → Lambda (ledger)

Failed messages → DLQ → ops alert + retry later
```

---

## Comparison with Standard Tools

### SQS vs Kafka

| Aspect | SQS | Kafka |
|---|---|---|
| Type | Managed queue service | Self-hosted message broker |
| Throughput | 300K msg/sec (standard) | 1M+ msg/sec (cluster-dependent) |
| Latency | ~100ms | ~10–50ms |
| Durability | Automatic (multi-AZ replicated) | Depends on replication factor |
| Ordering | FIFO queues (per partition) | Strict per-partition ordering |
| Consumer lag tracking | No built-in | Built-in |
| Operational burden | None (fully managed) | High (scaling, monitoring, backups) |
| Cost model | Pay per request | Pay for servers |
| Best for | AWS-native, async tasks | High-throughput, self-managed |

> SQS ≈ Kafka-as-a-service (managed, no ops burden, slightly slower).

---

### SNS vs RabbitMQ vs Redis Pub/Sub

| Aspect | SNS | RabbitMQ | Redis Pub/Sub |
|---|---|---|---|
| Type | Managed pub/sub | Self-hosted broker | In-memory pub/sub |
| Persistence | None | Yes (queues) | None (ephemeral) |
| Delivery | Instant fan-out | Must subscribe before publish | Must be listening |
| Ordering | No | Per-exchange | Per-channel |
| Latency | ~10–100ms | ~10–50ms | < 1ms |
| Operational burden | None | Medium (HA, clustering) | Medium |
| Cost | Per-request | Server-based | Server-based |

> SNS ≈ RabbitMQ / Redis Pub/Sub but fully managed and serverless.

---

### EventBridge vs Apache Kafka Streams

| Aspect | EventBridge | Kafka Streams |
|---|---|---|
| Pattern matching | Yes (content-based rules) | Yes (stream processing) |
| Schema validation | Yes (built-in registry) | No (manual) |
| Built-in integrations | 200+ AWS/SaaS | Limited |
| Operational burden | None (fully managed) | High |
| Latency | ~100ms | ~10–50ms |
| Cost | Per-event | Server-based |

> EventBridge ≈ Kafka Streams but fully managed, with SaaS integrations, and no tuning required.

---

## Lambda & Compute

### What is Lambda?

AWS's Function-as-a-Service (FaaS). You write a function, upload it, AWS runs it in response to events. You pay only for the milliseconds your code executes.

**Mental model:**

```
Event (SQS, S3, HTTP, …)
  ↓
AWS Lambda: spin up container → run function → shut down
  ↓
Result (success or error)

Cost: ~$0.0000002 per 100ms
```

### Lambda Limits

| Limit | Value |
|---|---|
| Execution timeout | 15 minutes |
| Memory | 128 MB – 10 GB |
| Payload (sync) | 6 MB |
| Payload (async) | 256 KB |
| Concurrent executions | 1,000 / region (default) |
| Temp storage (`/tmp`) | 512 MB |
| Cold start | 100–500ms |

**When NOT to use Lambda:**

| Requirement | Alternative |
|---|---|
| Job runs > 15 min | Step Functions, ECS, or EC2 |
| Memory > 10 GB | EC2 or containers |
| Latency < 10ms | Containers or EC2 |
| GPU needed | EC2 GPU or SageMaker |

### Lambda Concurrency

Concurrency = number of Lambda instances running simultaneously. Default: **1,000 per region**.

```
What happens at the limit?
  Synchronous calls → 429 ThrottledException
  Async calls (SQS, SNS) → retried automatically

Rule of thumb:
  1,000 simultaneous users → need ~1,000 reserved concurrency
  EventBridge + SQS + Lambda → SQS buffers load; Lambda auto-scales
```

---

## Data Storage

### DynamoDB vs RDS

| Aspect | DynamoDB | RDS (PostgreSQL/MySQL) |
|---|---|---|
| Type | NoSQL key-value / document | Relational database |
| Scaling | Automatic, horizontal | Manual (vertical or read replicas) |
| Consistency | Eventual (configurable to strong) | Strong (ACID) |
| Schema | Flexible | Strict |
| Joins | No (single-table access patterns) | Full SQL joins |
| Cost model | Pay per read/write | Pay per server hour |
| Best for | High-scale, simple queries | Complex queries, transactions |

### When to Use DynamoDB

- High throughput (100K+ reads/sec)
- Simple queries (get by ID, filter by one key)
- Unstructured / JSON documents
- Unpredictable or bursting traffic

### When to Use RDS

- Complex queries (multiple joins, aggregations)
- ACID transactions (money transfers must be atomic)
- Structured data with relationships
- Predictable, moderate throughput

### DynamoDB Single-Table Design

Store all app data in one table using composite primary keys.

**Example:**

| PK | SK | Data |
|---|---|---|
| `USER#123` | `PROFILE` | `{name, email, …}` |
| `USER#123` | `ORDER#456` | `{amount, date, …}` |
| `USER#123` | `ORDER#789` | `{amount, date, …}` |
| `ACCOUNT#acc-1` | `SETTINGS` | `{region, language}` |
| `ACCOUNT#acc-1` | `INVOICE#2024` | `{total, items, …}` |

```
Query all orders for USER#123:
  PK = "USER#123" AND SK begins_with "ORDER"

Query all data for ACCOUNT#acc-1:
  PK = "ACCOUNT#acc-1"
```

---

## Troubleshooting

### Lambda is slow / "Cold start"

**Problem:** First invocation takes 300–500ms; subsequent ones take 10–50ms.

**Why:** AWS spins up a container, loads code, initializes. That overhead is the "cold start."

**Solutions:**

| Option | Trade-off |
|---|---|
| Provisioned concurrency | Pay to keep Lambdas always warm |
| Minimize package size | Don't ship unnecessary dependencies |
| Lazy-import heavy libraries | Import inside handler, not at module level |
| Tolerate cold starts | For async workloads, users don't notice 500ms |

---

### SQS messages are being reprocessed

**Problem:** Same message received twice in your Lambda.

**Why:** Lambda failed to delete the message, or visibility timeout expired.

**Solutions:**

1. Make Lambda **idempotent** — handle duplicates gracefully
2. Increase visibility timeout if Lambda takes > 30 seconds
3. Use SQS FIFO + deduplication (5-min dedup window)
4. Store processed message IDs in DynamoDB as idempotency keys

---

### EventBridge rule isn't routing my event

**Problem:** Event published, but target Lambda/SQS doesn't receive it.

**Debug steps:**

1. EventBridge console → Rules → click rule → view event pattern
2. Use "Test event pattern" with a sample event
3. Check the dead-letter queue (if configured)

**Common mistakes:**

```json
// Wrong — string instead of array
{ "source": "myapp" }

// Correct
{ "source": ["myapp"] }
```

```
Typo: "type" vs "eventType" — both are valid field names,
but the rule must match exactly what the producer sends.
```

---

### DynamoDB is throttled

**Problem:** Lambda gets `ProvisionedThroughputExceededException` (HTTP 400).

**Why:** Ran out of read/write capacity.

**Solutions:**

| Solution | Notes |
|---|---|
| Enable autoscaling | Set min/max; DynamoDB scales automatically |
| Switch to on-demand billing | Pay per request, no capacity planning |
| Optimize queries | Avoid full-table scans; use GSIs |

---

## Architecture Decision Flow

```
I need to decouple services. What should I use?

Do they need to communicate in real-time (user sees result instantly)?
├─ YES → HTTP / Lambda-to-Lambda synchronous call
└─ NO  ↓

Does the message need to survive if the consumer is down?
├─ YES → SQS (durable storage)
└─ NO  → SNS (ephemeral, instant)

Do I need routing/filtering based on message content?
├─ YES → EventBridge
└─ NO  ↓

Do I have multiple independent subscribers (fan-out)?
├─ YES → SNS or EventBridge
└─ NO  → SQS

Summary:
  Durable buffer for async tasks  → SQS
  Instant broadcast               → SNS
  Smart routing                   → EventBridge
  Fan-out + durability            → EventBridge → SQS
```

---

## Key Takeaways

| Service | Mental model | Use when |
|---|---|---|
| SQS | Durable inbox, consumers pull | Async tasks, decoupling, retries |
| SNS | Instant broadcast to many | Push notifications, always-on fan-out |
| EventBridge | Smart router with rules | Pattern-based routing, SaaS integrations, cron |
| Lambda | Run code on events, pay per ms | Event-driven functions, < 15 min |
| DynamoDB | Serverless NoSQL, auto-scale | High throughput, simple access patterns |

**Default pattern for most serverless apps:**

```
EventBridge (entry) → SQS (durability) → Lambda (processing)
```

---

## Further Reading

- [AWS Messaging & Queuing](https://aws.amazon.com/messaging/)
- [SQS vs SNS Whitepaper](https://docs.aws.amazon.com/whitepapers/latest/messaging-between-aws-services/)
- [EventBridge Documentation](https://docs.aws.amazon.com/eventbridge/)
- [Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [DynamoDB Design Patterns](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)

---

## Questions?

Open an issue on the thinking-serverless GitHub:
<https://github.com/Emilio-Gordillo-Esparragoza/thinking-serverless/issues>
