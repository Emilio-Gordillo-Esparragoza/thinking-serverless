<h1 align="center">
  <span style="color: #ff9900; font-size: 3rem;">thinking Serverless</span>
</h1>

<p align="center">
  <em>A way to learn Serverless through foundational concepts and hands-on projects you can replicate, "Serverless Development on AWS" by Brisals & Hedger is the main reference for this repo. For more practical information, look at the <a href="./docs">docs/</a> and <a href="./domains">domains/</a> directories where these principles are applied.</em>
</p>

## 📑 Index

1. [What is Serverless?](#1-what-is-serverless)
2. [Translating AWS](#2-translating-aws)
3. [Software Architecture & Documentation for Serverless](#3-software-architecture--documentation-for-serverless)
   - [Architectural patterns & design principles](#architectural-patterns--design-principles)
   - [Hexagonal / Clean Architecture deep dive](#hexagonal--clean-architecture-deep-dive)
   - [Event‑driven architectures](#event‑driven-architectures)
   - [Monolith vs Microservices in Serverless](#monolith-vs-microservices-in-serverless)
   - [MACH & API‑first design](#mach--api‑first-design)
   - [Documentation that saves projects (and careers)](#documentation-that-saves-projects-and-careers)
4. [System Design Basics](#4-system-design-basics)
5. [Security](#5-security)
6. [Domains — Financial Fan-Out Example](#6-domains--financial-fan-out-example)

---

## 1. What is Serverless?

The **Serverless** model goes beyond “no servers to manage”. It's a paradigm shift where you pay only for what you use (**pay-as-you-go**), with no charges for idle time. Within the cloud computing spectrum we find:

- **IaaS** (Infrastructure as a Service): EC2, VPC – you manage the OS and runtime.
- **PaaS** (Platform as a Service): Elastic Beanstalk – you only deploy code.
- **Serverless** (Function as a Service + managed services): Lambda, API Gateway, S3 – you don't even see the infrastructure.

### Parts of a Serverless Project

A real project includes:

- **Cloud platform** (AWS, Azure, GCP)
- **Serverless services** (Lambda, DynamoDB, SQS, etc.)
- **Architecture** (hexagonal, event‑driven, etc.)
- **Infrastructure definition** (IaC)
- **Development & testing tools** (localstack, floci, SAM)
- **Repositories & pipelines** (GitHub Actions, GitLab CI)
- **Observability** (CloudWatch, X-Ray, OpenTelemetry)
- **Best practices** – for instance, the [AWS Well-Architected Framework](https://aws.amazon.com/well-architected-framework/)
- **Contributors & stakeholders** (developers, security teams, product)

### GUI vs IaC: why Infrastructure as Code matters

You can create everything from the **AWS Dashboard** (click by click), but soon you'll find that **IaC** is much better:

- **Terraform**, **CloudFormation** or **Ansible** define the whole architecture as text.
- You can **automate deployments** with GitHub Actions (merging to `main` updates everything).
- With a single command (`terraform destroy` or `sam delete`) you shut down everything and **stop paying**.
- **Local testing** before deploying: [LocalStack](https://www.localstack.cloud/) or [floci](https://github.com/floci-io/floci-cli) simulate AWS on your machine with zero cost.

> **What is SAM?**  
> AWS SAM (Serverless Application Model) is an open‑source framework to define Lambda functions, API Gateway, and more using simplified CloudFormation. It includes local emulation with `sam local start-api`.

---

## 2. Translating AWS

**Fully managed** ≠ Serverless, although they often overlap. A *fully managed* service is operated by AWS (patches, scaling), but it may run on servers all the time (e.g., RDS). Serverless implies *scale to zero* and pay‑per‑use.

| Service        | What it does (simplified)                                  | Serverless? |
|----------------|------------------------------------------------------------|--------------|
| **Lambda**     | FaaS: runs code in response to events.                    | ✅ Yes       |
| **RDS**        | Managed relational database (PostgreSQL, MySQL).          | ❌ (but fully managed) |
| **EC2**        | Virtual machines; you choose AMI, size, etc.              | ❌           |
| **ECS**        | Container orchestration (Docker) on EC2 clusters or Fargate. | Depends (Fargate = yes) |
| **API Gateway**| HTTP/S entry point for Lambda or other backends.          | ✅ Yes       |
| **VPC**        | Isolated virtual network.                                 | ❌ (fully managed) |
| **IAM**        | Access control (users, roles, policies).                  | ✅ Yes       |
| **SNS**        | Pub/Sub notifications.                                    | ✅ Yes       |
| **SQS**        | Message queue (decoupling).                               | ✅ Yes       |
| **EventBridge**| Event bus (cron, SaaS, AWS services).                     | ✅ Yes       |
| **S3**         | Object storage.                                           | ✅ Yes       |
| **Cognito**    | Authentication & identity federation.                     | ✅ Yes       |
| **DynamoDB**   | NoSQL key‑value and document database.                    | ✅ Yes       |
| **Step Functions** | Visual workflows for distributed applications.         | ✅ Yes       |

### When to use EC2 or ECS instead of Lambda?

- **Lambda** has a 15‑minute execution timeout and 10 GB of memory. Ideal for short processes, async events, lightweight APIs.
- **EC2** or **ECS** (with Fargate or EC2 launch type) is needed when:
  - You need more than 15 minutes or more than 10 GB of RAM.
  - You use languages/runtimes not supported by Lambda (e.g., Windows, GPU).
  - You have highly predictable, long‑running workloads (a traditional web server).
  - You require fine‑grained control over the kernel, networking, or ephemeral storage.

> Rule of thumb: **start with Lambda**; only move to containers or VMs if you hit its limits.

---

## 3. Software Architecture & Documentation for Serverless

Good architecture accelerates development, simplifies testing, and eases maintenance. **Documentation is not an afterthought** – it is a living part of the architecture that prevents tribal knowledge and enables teams to scale.

### Architectural patterns & design principles

The following principles and patterns form the backbone of successful serverless applications:

- **Separation of concerns** – business logic lives in a domain layer, infrastructure in adapters (hexagonal). This allows you to test the core without any cloud resources.
- **Loose coupling** – services communicate via events or queues, not direct calls. This enables independent evolution and failure isolation.
- **Statelessness** – functions don’t hold state between invocations; state is externalized to DynamoDB, S3, or ElastiCache.
- **Idempotency** – every event handler should be safe to retry. Use idempotency tokens or natural keys to prevent duplicate side effects.
- **Single‑table design in DynamoDB** – model access patterns first, then design keys (PK/SK) and secondary indexes to support multiple entity types in one table.

### Hexagonal / Clean Architecture deep dive

The hexagonal (ports & adapters) architecture is a natural fit for serverless because it treats cloud services (SQS, API Gateway, S3) as external “adapters” that plug into your business logic.

A typical **serverless hexagonal structure** looks like:
```
├── src/
│ ├── domain/
│ │ ├── models/
│ │ └── services/
│ ├── ports/
│ │ └── interfaces/
│ ├── adapters/
│ │ ├── inbound/
│ │ └── outbound/ 
│ └── infrastructure/ 
└── tests/
├── unit/ 
└── integration/
```

**Benefits**:
- The domain code is **framework‑free** and can be reused across Lambda, Step Functions, or even containerised runtimes.
- Switching a database from DynamoDB to Cosmos DB only requires a new adapter – the domain logic remains untouched.
- **Testing speed**: domain unit tests run in milliseconds, not seconds, because they don’t spin up infrastructure.

### Event‑driven architectures

Serverless shines with event‑driven systems. Instead of choreographing every step, services emit events and react to them.

- **Choreography**: each service emits domain events (e.g., `OrderPlaced`) to EventBridge; other services subscribe independently. Great for autonomous teams.
- **Orchestration**: Step Functions coordinate a long‑running saga, managing retries, compensations, and human approvals. Perfect for business processes like order fulfillment.
- **Dead Letter Queues (DLQ)**: always attach a DLQ to Lambda or SQS to capture failed events for later inspection and replay.

**Event design rules**:
- Events should be **facts, not commands** (e.g., `PaymentCompleted`, not `ProcessPayment`).
- Include a **correlation ID** to trace a workflow end‑to‑end.
- Version events from day one (e.g., `v1.order.placed`), using an event bus rule to route older versions.

### Monolith vs Microservices in Serverless

In serverless, a “monolith” can be a single Lambda with several endpoints (managed with frameworks like FastAPI + Mangum) while still enjoying scale‑to‑zero. Microservices are natural, but premature decomposition is costly.

| When to use a Lambda monolith | When to split into separate Lambdas |
|-------------------------------|-------------------------------------|
| Single team, small domain     | Different teams own different subdomains |
| Low throughput, few endpoints | Independent scaling needs (e.g., high‑traffic search vs low‑traffic admin) |
| You need fast local dev loop with frameworks like Express/FastAPI | You want different failure isolation or security profiles |
| You’re prototyping or validating an idea | You need different deployment cadences |

**Decision heuristic**: Start with a well‑structured monolith that follows hexagonal principles. Only extract a Lambda microservice when a bounded context becomes clearly autonomous, or when a non‑functional requirement (performance, security, team velocity) forces a split. For practical examples and patterns on how to do this safely, see [monolith-to-microservices](https://github.com/Emilio-Gordillo-Esparragoza/monolith-to-microservices).

### MACH & API‑first design

**MACH** (Microservices, API‑first, Cloud‑native, Headless) is a philosophy that aligns perfectly with serverless.

- **API‑first**: Design the API contract (OpenAPI) before writing a single line of backend code. This contract becomes a source of truth for frontend, mobile, and third‑party developers.
- **Headless**: The backend exposes pure APIs; the frontend is entirely decoupled, often a Jamstack app hosted on S3 + CloudFront.
- **Cloud‑native**: All services are managed (S3, DynamoDB, Cognito), requiring zero maintenance.

Implementing API‑first with serverless:
1. Draft the OpenAPI specification collaboratively using tools like [Stoplight Studio](https://stoplight.io/) or [Swagger Editor](https://editor.swagger.io/).
2. Generate TypeScript/Python client SDKs from the spec and share them with frontend teams.
3. Use the spec to configure **API Gateway request validation** – it will reject invalid payloads before they reach Lambda, saving cost and reducing attack surface.
4. Generate mock integrations in API Gateway so that frontend developers can work immediately without a deployed backend.

### Documentation that saves projects (and careers)

Documentation is a **force multiplier**. In serverless, where logic is distributed across many services, the ability to quickly understand the system’s behaviour becomes a critical capability.

Adopt a **“documentation as code”** mindset: everything lives in the repository, is version‑controlled, reviewed, and automatically published.

#### Types of documentation and when to create them

1. **Architecture Decision Records (ADRs)**  
   - **What**: Markdown files that capture a significant architectural decision, the context, the options considered, and the trade‑offs.
   - **When**: At every major fork in the design (e.g., “Chose DynamoDB over RDS for user sessions because of access patterns and scale‑to‑zero cost”).
   - **Why**: ADRs prevent endless re‑debates when new team members join. They document the “why” behind the architecture.

2. **C4 model diagrams** (Context, Containers, Components, Code)  
   - **Level 1 – Context**: Shows the system, its users, and external systems. Suitable for business stakeholders and CTOs.
   - **Level 2 – Containers**: The high‑level technical building blocks (e.g., “React SPA”, “API Gateway”, “Orders Lambda”, “DynamoDB”). Perfect for architects and new developers.
   - **Level 3 – Components**: The inside of a container – Lambda functions, SQS queues, Step Functions state machine. Used by developers during feature work.
   - **Level 4 – Code** (optional): UML class/sequence diagrams generated from the code or maintained sparingly.
   - **Tooling**: Use [Structurizr DSL](https://structurizr.com/) or PlantUML committed next to the code. Diagrams are rendered in the CI pipeline and published to the repo’s wiki.

3. **API documentation (OpenAPI / AsyncAPI)**  
   - REST and HTTP APIs use **OpenAPI 3.x**. The spec is the source of truth, generating both human‑readable docs (Swagger UI) and SDKs.
   - Event‑driven systems use **AsyncAPI** to document the channels (SQS, EventBridge) and message schemas. Treat it as the “event contract” between producers and consumers.
   - **Pro tip**: Run a breaking‑change check on the spec in CI (e.g., [openapi-diff](https://openapi.tools/#diff)) to avoid accidentally breaking clients.

4. **README‑driven development**  
   - Write the README for a service *before* coding. Describe what it does, the API/events it exposes, how to run it locally, and how to deploy it. This forces clarity.
   - A strong README answers: “What problem does this service solve? How do I get started in 5 minutes? How do I run tests? Where are its logs?”

5. **Docstrings and living documentation**  
   - Docstrings explain **why** a function exists, not just what it does. Link to the ADR or the business requirement.
   - Use tools like [mkdocs](https://www.mkdocs.org/) to generate a static documentation site from Markdown and docstrings, deployed automatically to S3/CloudFront.
   - Embed **diagrams as code** (Mermaid) directly in Markdown files – they render natively on GitHub and GitLab.

6. **Runbooks and incident documentation**  
   - For each service, document common failure scenarios, alert conditions, and step‑by‑step diagnosis (e.g., “If `payment‑processed` DLQ grows, check the Stripe webhook logs…”).
   - Store these in the same repository, under a `/docs` folder, so they evolve with the code.

> **Good documentation speeds up onboarding, reduces pager noise, and makes your system maintainable years after its creators have moved on.**

---

## 4. System Design Basics

System design is about choosing the right trade-offs for reliability, latency, scalability, and cost. In serverless, the same principles still apply, but the implementation usually shifts toward managed services, event-driven flow, and explicit boundaries between compute, storage, and data access.

### Core ideas to keep in mind

- **Scalability**: design for horizontal growth rather than relying on a single large instance.
- **Reliability**: avoid single points of failure and prefer services with built-in redundancy.
- **Latency**: move data closer to the user and reduce unnecessary round trips.
- **Cost efficiency**: pay for work actually done, but avoid expensive patterns that create waste.
- **Operational simplicity**: let managed services handle patching, scaling, and backups where possible.

### Databases: the basics

A classic database design question is whether to choose a relational or a NoSQL model. In practice, the right answer depends on access patterns, consistency requirements, and team experience.

| Pattern / concept | What it means | Serverless-friendly approach |
|---|---|---|
| **Primary / replica** | One writer handles updates, replicas serve reads | Use managed read replicas or event-driven projections |
| **Master / slave** | A primary node writes while replicas offload read traffic | Often replaced by managed database replicas or CQRS-style patterns |
| **SQL database** | Strong consistency and joins for structured data | Use RDS, Aurora, or Aurora Serverless for transactional workloads |
| **NoSQL database** | Flexible schemas and high scale for key/value or document access | Use DynamoDB for high-throughput, low-ops workloads |

> In serverless, database design often matters more than the database brand. The biggest win is choosing a model that matches the way your application actually reads and writes data.

### Load balancers and entry points

A load balancer is not only for traditional VMs. In serverless architectures, your “front door” often looks like one of these:

- **API Gateway** — ideal for HTTP APIs, request validation, throttling, and auth.
- **Application Load Balancer (ALB)** — useful when you run containers or need advanced routing.
- **Network Load Balancer (NLB)** — better for TCP/UDP-style workloads or lower-level traffic patterns.

For serverless, the important idea is that the entry point should handle routing, auth, and protection before traffic reaches your functions.

### Database replication and availability

Replication helps improve resilience and read performance.

- **Multi-AZ** deployment protects against region or availability-zone failures.
- **Read replicas** reduce load on the primary database for reporting or read-heavy flows.
- **Eventual consistency** is normal in many serverless designs, especially when using event-driven systems.
- **Backups and restore plans** are still required, even when the platform is managed.

### Cache tiers

Caching is one of the best ways to improve performance without adding much complexity.

- **Edge cache**: CloudFront or CDN layers reduce latency for geographically distributed users.
- **Application cache**: Redis or ElastiCache stores hot data for quick access.
- **Database cache**: DynamoDB Accelerator (DAX) or similar patterns can help reduce repeated read pressure.
- **TTL policies**: set short expiration times for data that changes often.

### Rate limits and protection

A good system design basics section should include limits so that a burst of traffic does not break everything.

- **API Gateway quotas** can limit requests per second or per minute.
- **WAF** protects against abusive or malicious traffic.
- **Concurrency controls** on Lambda help prevent runaway costs and resource exhaustion.
- **Queues** (SQS, EventBridge, Step Functions) help absorb spikes and apply backpressure.

### Serverless design takeaway

The serverless version of good system design is usually:

1. Put a managed entry point in front of your services.
2. Keep business logic stateless and event-driven.
3. Use managed data stores that match your access pattern.
4. Add caching and rate limiting to protect performance and cost.
5. Treat failures as normal and design around retries, queues, and observability.

---

## 5. Security

> "Security is a process, not a product" — Bruce Schneier

Thinking like a **hacker** during design is one of the best ways to secure your applications. Most common vulnerabilities are exploited because someone did not imagine that path.

### Fundamental principles

- **Zero Trust** — trust no one, neither inside nor outside the network.
- **Least Privilege** — each role, user, or function has exactly the minimum permissions required.
- **Security Groups & Policies** — use security groups (instance-level firewalls) and restrictive IAM policies.
- **OWASP Top 10 for Serverless** — pay special attention to:
  - Event injection
  - Broken authentication
  - Exposure of secrets (never store them in code; use Secrets Manager or Parameter Store)

### STRIDE: A framework for security

STRIDE stands for:

- **Spoofing** — pretending to be someone or something you are not.
- **Tampering** — changing data in storage, memory, or on the network.
- **Repudiation** — denying or disputing that an action happened.
- **Information disclosure** — exposing data to someone who should not see it.
- **Denial of service** — exhausting finite resources so that the service becomes unavailable.
- **Elevation of privilege** — performing actions that should not be allowed, such as gaining admin or root access.

A common way to apply this framework is **STRIDE-per-element**, where the threat categories are mapped to the elements in your application.

| Element | S | T | R | I | D | E |
|---|---|---|---|---|---|---|
| Human actor / external entity | ✅ |  | ✅ |  |  |  |
| Process | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Data store |  | ✅ | ✅ | ✅ | ✅ |  |
| Data flow |  | ✅ |  | ✅ | ✅ |  |

> **How this applies to our fan-out architecture:** The EventBridge bus is the central nervous system of the system. A single tampered event can poison compliance, fraud, and ledger flows. IAM roles should be scoped per domain (for example, orchestration writes while consumers only read). SQS DLQs help contain poison-pill messages, and CloudTrail plus EventBridge archives improve non-repudiation.

### Beyond STRIDE: SLSA (SALSA)

SLSA (Supply-chain Levels for Software Artifacts, pronounced *salsa*) is a security framework from Google that helps protect the software supply chain — the path from source code to deployed artifact.

**Why it matters for serverless:** Your Lambda functions, container images, and IaC templates are built from dependencies such as pip packages, base images, and GitHub Actions workflows. SLSA provides a maturity model to help ensure that what you deploy is exactly what was reviewed and that no one tampered with it along the way.

**SLSA levels (1–4):**

| Level | Requirement | Serverless example |
|---|---|---|
| **1** | Build process is scripted and documented | CI pipeline with `pip install -r requirements.txt` |
| **2** | Build runs on a hosted platform with provenance | GitHub Actions generates a signed provenance attestation |
| **3** | Hardened build platform and prevention of tampering | Hermetic builds, no network access during build, and two-person review for IaC PRs |
| **4** | Build is fully hermetic and dependencies are verified | Pin dependency hashes, sign container images with cosign, and enforce `verify` during Lambda layer deployment |

### Protecting the API and data

- **API Gateway** → WAF (AWS Web Application Firewall) + rate limiting (throttling) + strict request validation against the OpenAPI spec.
- **Data**:
  - Encryption in transit (TLS) and at rest (KMS).
  - Use DynamoDB or RDS with VPC‑restricted access.
  - Avoid storing unnecessary sensitive information; tokenize or hash.
- **Production**:
  - Separate environments (dev/staging/prod) with different AWS accounts (AWS Organizations).
  - Audit with CloudTrail and GuardDuty.
  - Security pipeline: SAST (static analysis), DAST (dynamic), and dependency scanning (e.g., Snyk, Dependabot).

> **Good habit**: always write a “Threat modeling” section in your design documentation. What would happen if someone sends 10,000 requests per second? What if a Lambda can read S3 objects from another tenant? Document the mitigations and keep them updated.
---

## 6. Domains — Financial Fan-Out Example

This repository separates reusable **domain modules** under [`domains/`](./domains/)
from **example composition roots** under [`examples/`](./examples/). The first
example implements the **EventBridge + SQS fan-out pattern** for financial
transactions.

- [`domains/finance_orchestration/`](./domains/finance_orchestration/) – entry
  point Lambda + EventBridge bus and rules.
- [`domains/finance_compliance/`](./domains/finance_compliance/) – AML
  screening consumer.
- [`domains/finance_fraud/`](./domains/finance_fraud/) – fraud scoring
  consumer.
- [`domains/finance_ledger/`](./domains/finance_ledger/) – double-entry
  ledger consumer.
- [`domains/finance_monolith/`](./domains/finance_monolith/) – synchronous
  comparison stack (deploy separately).
- [`shared/`](./shared/) – reusable IAM policies, event schemas, and Python
  utilities.

See [`examples/fanout/README.md`](./examples/fanout/README.md) for full
architecture diagrams, one-command deployment instructions, and a comparison
of synchronous vs asynchronous fan-out.
