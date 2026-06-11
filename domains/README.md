# Domains — Financial Fan‑Out Pattern

## The Problem with Synchronous Order Processing

A financial company processed every transaction through a single monolithic
Lambda triggered by API Gateway:

```
Client
  │
  ▼
API Gateway
  │
  ▼
newOrder Lambda (catch‑all)
  │
  ├── Capture order data
  │
  ├── If amount > $10,000 → call Compliance API (wait)
  │     └── if flagged → reject
  │
  ├── If transfer → call Fraud API (wait)
  │     └── if suspicious → hold
  │
  └── Update ledger (wait)
        └── if ledger down → entire transaction fails
```

**What went wrong:**

- **Latency stacked** — the client waited while Compliance called external AML
  databases, Fraud calculated scores, and the ledger committed. A simple deposit
  took seconds because the slowest service dragged the whole chain.
- **Cascade failures** — when the ledger went down during a batch reconciliation,
  every new transaction failed, even deposits that had zero ledger impact.
  Compliance and Fraud checks already passed, but their work was wasted.
- **Bottleneck at scale** — the single `newOrder` Lambda handled ordering,
  compliance, fraud, and ledger logic. The team feared touching it because a
  bug in any branch took down the entire flow.
- **No audit trail** — if a transaction failed midway, there was no record of
  what passed and what didn't. Operations spent hours replaying logs to figure
  out where each transaction stopped.

The company needed a way to decouple these concerns so that each one could
fail, scale, and deploy independently — without the client waiting for all of
them.

Under the **domain‑based monorepo**, each business capability lives in its own
directory with its own source code and infrastructure:

```
domains/
├── finance-compliance/      # AML screening
│   ├── src/
│   └── infrastructure/
│       ├── terraform/
│       └── sam/
├── finance-fraud/           # Fraud scoring
│   ├── src/
│   └── infrastructure/
│       ├── terraform/
│       └── sam/
├── finance-ledger/          # Double‑entry bookkeeping
│   ├── src/
│   └── infrastructure/
│       ├── terraform/
│       └── sam/
└── finance-orchestration/   # Transaction entry point & EventBridge rules
    ├── src/
    └── infrastructure/
        ├── terraform/
        └── sam/
```

---

## Architecture: EventBridge + SQS Financial Fan‑Out

```
  Client
    │
    ▼
API Gateway ──► process_transaction (finance-orchestration)
                    │
                    ▼ put_event
            ┌─ EventBridge (finance-events) ─┐
            │          │                     │
            ▼          ▼                     ▼
    Compliance SQS ─ Fraud SQS ──────── Ledger SQS
         │              │                    │
         ▼              ▼                    ▼
  compliance_check  fraud_detection    ledger_update
  (finance-         (finance-fraud)    (finance-ledger)
   compliance)
         │              │                    │
         ▼              ▼                    ▼
        DLQ            DLQ                  DLQ
```

Every transaction flows through a single entry point
(`process_transaction`), which validates the payload and publishes an event.
EventBridge fans out to three SQS queues, each consumed independently by its
domain's Lambda. Failures land in a Dead‑Letter Queue for later inspection.

---

## Deployment Order

The domains have a **cross‑domain dependency**: `finance-orchestration` needs
the SQS queue ARNs from the other three domains to wire up EventBridge rules.

### Option A: Terraform (two-stage)

**Stage 1** – Deploy the three consumer domains first to obtain queue ARNs:

```bash
# 1. Compliance
cd domains/finance-compliance/infrastructure/terraform
terraform init
terraform apply -var="environment=dev"
# Note the compliance_queue_arn output

# 2. Fraud
cd ../../finance-fraud/infrastructure/terraform
terraform init
terraform apply -var="environment=dev"
# Note the fraud_queue_arn output

# 3. Ledger
cd ../../finance-ledger/infrastructure/terraform
terraform init
terraform apply -var="environment=dev"
# Note the ledger_queue_arn output
```

**Stage 2** – Deploy the orchestration domain, passing the queue ARNs:

```bash
cd ../../finance-orchestration/infrastructure/terraform
terraform init
terraform apply \
  -var="environment=dev" \
  -var="compliance_queue_arn=arn:aws:sqs:..." \
  -var="fraud_queue_arn=arn:aws:sqs:..." \
  -var="ledger_queue_arn=arn:aws:sqs:..."
```

### Option B: SAM (parameterised templates)

```bash
# Deploy consumer domains first
cd domains/finance-compliance/infrastructure/sam
sam deploy --guided  # note the ComplianceQueueArn output

cd ../../finance-fraud/infrastructure/sam
sam deploy --guided  # note the FraudQueueArn output

cd ../../finance-ledger/infrastructure/sam
sam deploy --guided  # note the LedgerQueueArn output

# Deploy orchestration, passing queue ARNs as parameters
cd ../../finance-orchestration/infrastructure/sam
sam deploy \
  --parameter-overrides \
    ComplianceQueueArn=arn:aws:sqs:... \
    FraudQueueArn=arn:aws:sqs:... \
    LedgerQueueArn=arn:aws:sqs:... \
    Environment=dev
```

---

## Synchronous vs Asynchronous Fan‑Out

### Synchronous (the old way — bad for finance)

```
Client ──► API Gateway ──► newOrder Lambda
                              │
                              ├── capture data ──────────────────┐
                              ├── Compliance API ── wait ────────┤
                              ├── Fraud API ─────── wait ────────┤── response
                              └── Ledger API ────── wait ────────┘
```

**Problems:**
- **Total latency** = sum of all three services. The client waits until every
  downstream system has finished.
- **Cascade failure** – if Ledger is down, the whole transaction fails, even
  though Compliance already passed.
- **Hard to scale** – every consumer must keep up with the same throughput,
  or the slowest one becomes the bottleneck.
- **Tight coupling** – adding a fourth domain (e.g., `finance-reporting`)
  requires changing the orchestrator code.

### Asynchronous fan‑out (EventBridge + SQS)

```
Client ──► API ──► EventBridge ──► Compliance SQS ──► compliance_check
                ├──► Fraud SQS ───────────► fraud_detection
                └──► Ledger SQS ──────────► ledger_update
```

**Benefits:**
- **Client gets an instant 202** – the transaction is accepted and processed
  in the background.
- **Independent processing** – each consumer runs at its own pace. Fraud can
  be near‑real‑time while Ledger batches for efficiency.
- **Failure isolation** – a Ledger outage doesn't block Compliance or Fraud.
  Failed messages go to a DLQ for replay without data loss.
- **Elastic scaling** – SQS acts as a shock absorber. A traffic spike is
  buffered in the queue and drained at each consumer's pace.
- **Extensible** – adding a new domain is just a new SQS queue + rule in
  EventBridge; no orchestrator changes needed.

### When to use synchronous

- **Read operations** (query a balance, get transaction history).
- **Idempotent writes where latency is critical** (auth tokens, session
  creation).
- **Transactions that must succeed or fail atomically** (rare in distributed
  systems; consider Saga + Step Functions instead).

---

## Local Testing

Each Lambda has a companion `test_lambda.py` that can be run with Python's
built-in `unittest`:

```bash
# From the repository root
python -m pytest domains/finance-orchestration/src/process_transaction/test_lambda.py

python -m pytest domains/finance-compliance/src/compliance_check/test_lambda.py

python -m pytest domains/finance-fraud/src/fraud_detection/test_lambda.py

python -m pytest domains/finance-ledger/src/ledger_update/test_lambda.py
```

For integration testing, use [LocalStack](https://www.localstack.cloud/) or
[sam local invoke](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-cli-command-reference-sam-local-invoke.html).
