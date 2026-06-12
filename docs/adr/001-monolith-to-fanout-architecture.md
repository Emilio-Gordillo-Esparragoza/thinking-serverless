# ADR 001: Monolith to EventBridge Fan-Out Architecture

## Status
**Accepted**

## Context

The initial financial transaction processing system was implemented as a **synchronous monolith** — a single Lambda function that orchestrated all business logic:

```
Client → Lambda (monolith)
           ├─ 1. Transaction Validation   ~10ms   (fast)
           ├─ 2. Compliance Check         ~500ms–2s (slow, external AML API)
           ├─ 3. Fraud Detection          ~300–500ms
           └─ 4. Ledger Update            ~200–400ms
                                          ─────────────
                                          Total: 1–3s  ← client waits for all of it
```

### Problems with the Monolithic Approach

| Problem | Impact |
|---|---|
| **Latency stacking** | Clients waited for the slowest step (Compliance). A simple deposit took 2–4 seconds. |
| **Cascade failures** | If Ledger went down, ALL transactions failed — even when Compliance and Fraud had already passed. |
| **Tight coupling** | A change to one domain required testing and redeploying the entire orchestrator. |
| **No independent scaling** | All domains had to keep pace with the same throughput. The slowest became the bottleneck. |
| **Poor audit trail** | Partial failures left no clear record of which domains succeeded and which failed. |

## Decision

We adopt an **asynchronous, event-driven architecture** using **Amazon EventBridge** as the event bus and **AWS SQS** (Standard queues initially) as the decoupling layer between the orchestrator and domain consumers.

```
Client → Orchestration Lambda → 202 Accepted (immediately)
                ↓
          EventBridge (finance-events bus)
                ├─ Rule → SQS (compliance-queue) → Compliance Lambda
                ├─ Rule → SQS (fraud-queue)       → Fraud Lambda
                └─ Rule → SQS (ledger-queue)      → Ledger Lambda
                          (each runs independently, in parallel)
```

### Architecture Overview
![Fanout Architecture](../../diagrams/output/fanout_architecture.png)


## Rationale

### Why EventBridge over Direct Lambda-to-Lambda Calls?

- **Decoupling**: New consumers can subscribe without touching the orchestrator.
- **Replay capability**: We can replay events from EventBridge for testing or recovery.
- **Fan-out**: One event can trigger multiple independent workflows.

### Why SQS over SNS?

- **Durability**: SQS stores messages for up to 14 days; SNS requires immediate delivery.
- **Backpressure**: SQS queues act as shock absorbers for traffic spikes.
- **Per-domain scaling**: Each Lambda consumer scales independently based on queue depth.
- **Future-proof for ordering**: FIFO queues (not used in this example) can enforce strict ordering per partition key.

### Why 202 Accepted Response?

- Clients don't wait for domain processing to complete.
- If a client needs immediate feedback (e.g., "Account flagged for review"), a synchronous query endpoint answers that separately.
- Reduces Lambda execution time, lowering costs and improving resilience.

## Consequences

### Positive

1. **Independent scaling**: Each domain consumer scales based on its queue depth, not the orchestrator.
2. **Failure isolation**: A Ledger outage doesn't block Compliance or Fraud checks.
3. **Team autonomy**: Compliance team deploys changes without involving Fraud or Ledger teams.
4. **Extensibility**: Adding a fourth domain (e.g., `finance_reporting`) is a new SQS queue + EventBridge rule; no orchestrator changes.
5. **Cost efficiency**: Unused services don't run; each Lambda scales independently with traffic.

### Tradeoffs & Mitigation

| Challenge | Mitigation |
|-----------|-----------|
| **Eventual consistency** – domain state is no longer synchronized | Provide separate query APIs (read models) that each domain owns. Use a DynamoDB projection for reporting. |
| **Harder debugging** – request flow is no longer a single stack trace | Implement correlation IDs in events; use X-Ray for distributed tracing (ADR 002). |
| **Message deduplication** – what if a transaction is processed twice? | Implement idempotency patterns (ADR 003) with idempotency tokens stored in DynamoDB. |
| **Order dependencies** – what if Ledger must process transactions in strict order? | Use FIFO queues with a partition key = account ID (ADR 004). |

## Implementation Phases

### Phase 1: Basic Fan-Out (Current — Example 1)
- Standard SQS queues (no ordering).
- Basic Lambda error handling + generic DLQ.
- 202 Accepted client responses.

### Phase 2: Idempotency (Example 2)
- Idempotency decorator + DynamoDB idempotency store.
- Per-domain DLQs with visibility into failure reasons and retry policies.
- Exponential backoff retry policies.
- Add simple benchmarking using CI.

### Phase 3: FIFO & Ordering (Example 3)
- FIFO queues for Ledger (strict account-level ordering).
- Deduplication ID generation.
- Exactly-once semantics.

### Phase 4: Observability  (Example 4)
- AWS X-Ray tracing for end-to-end visibility.
- CloudWatch Insights dashboards for SLA monitoring.
- Custom metrics for domain-specific KPIs.

### Phase 5: Multi-Region Failover (Example 5)
- Cross-region event replication with EventBridge.
- Regional queue failover strategies.

## Alternatives Considered

| Alternative | Pros | Cons | Verdict |
|---|---|---|---|
| **Step Functions (sync orchestration)** | Manages retries and compensations natively | Still waits for all steps; ~100ms overhead per invocation; harder to replay mid-saga | Use for long-running sagas (> 2 min) requiring human approval — not for fast parallel fan-out |
| **SNS instead of SQS** | Simpler pub/sub model | No replay, no backpressure, requires immediate delivery | Use SNS for real-time webhooks or push notifications to external systems |
| **Direct Lambda invocation (async)** | No intermediate queue; low latency | No durability if Lambda throttled; no replay; tight coupling | Use only for truly synchronous critical paths (auth, authorization) |

## Related ADRs
- [ADR 002: Idempotency Pattern with DynamoDB](#) (future) 
- [ADR 003: FIFO Queues for Strict Ordering](#) (future)
- [ADR 004: Distributed Tracing with AWS X-Ray](#) (future)

## References
- [AWS Well-Architected Framework – Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)
- [AWS EventBridge Documentation](https://docs.aws.amazon.com/eventbridge/)
- [AWS SQS vs SNS](https://docs.aws.amazon.com/whitepapers/latest/messaging-between-aws-services/sqs-vs-sns.html)
- [Event Sourcing Pattern](https://martinfowler.com/eaaDev/EventSourcing.html)
