# Product Requirements: AI PDF Chatbot

Version 4.0 | 2026-11-13 | Planning baseline; not implemented

## 1. Goal and delivery scope

Build an authenticated PDF question-answering application for a portfolio, with production-oriented service boundaries, durable processing and private document access. Develop locally without a dedicated GPU; prepare for GPU-backed staging/production later. The main stack is fixed in [TECH_STACK.md](TECH_STACK.md), architecture in [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md), and delivery in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).

Three distinct outcomes: **local implementation/demo**, **deployment preparation when needed**, and **production verification on representative resources**. Local completion does not require a GPU rental, Kubernetes cluster, Terraform deployment or a 5,000-RPS benchmark. The original 15-day learning schedule is not a delivery commitment.

## 2. User flow

Sign in -> upload PDF -> track indexing -> select private ready documents -> submit a self-contained question -> track answer job -> read answer and sources -> reconnect, retry/cancel or delete.

Initial users have private libraries; shared workspaces are excluded. Questions are independent. Short-lived saved results support reconnect, not long-term conversation memory. English text is the initial evaluation scope.

## 3. Requirements and acceptance

| ID | Requirement | Acceptance |
| --- | --- | --- |
| FR-01 | Bounded, immutable PDF uploads | Reject non-PDF, encrypted, oversized, over-page-limit and entirely textless input; flag textless pages in mixed PDFs. Accepted bytes cannot change through upload URL reuse. |
| FR-02 | Durable ingestion | Accepted jobs survive API/worker restarts; retries do not expose partial indexes or duplicate visible work. |
| FR-03 | Owner-scoped duplicates | Identical bytes return the same owner's existing document; reveal nothing about another owner's copy. |
| FR-04 | Persistence | Documents and recent job results survive application replica replacement. |
| FR-05 | Authentication and isolation | Every document, job, source, retry, download and deletion operation enforces authenticated ownership. |
| FR-06 | Grounded answers | Retrieve only selected ready versions; unsupported questions explicitly acknowledge insufficient evidence. |
| FR-07 | Verifiable citations | Supported answers include server-resolved filename, original 1-based PDF page index and exact supplied excerpt. |
| FR-08 | Reconnect | After losing all UI session state, discover recent owner jobs and available results through a paginated API. |
| FR-09 | Safe deletion | Accepted deletion immediately excludes content from new reads; durable cleanup removes files/vectors/results without allowing stale-worker resurrection. |
| FR-10 | Resource/admission limits | Bound uploads, model context, queues, quotas, deadlines and retries; return actionable overload errors. |
| FR-11 | Untrusted source content | PDF instructions cannot authorize actions; model has no browsing, shell or filesystem tools. |
| FR-12 | Clear interface | Show processing/model mode, failures, queue state, PDF-page numbering, retention and unsupported-file limitations. |
| FR-13 | Operability | Sanitized logs/metrics, correlation, readiness and recovery checks exist without default content logging. |

## 4. Quality and evidence

Local completion requires reproducible setup, authenticated end-to-end behavior, meaningful unit/real-storage integration tests, failure/retry/deletion/reconnect checks, and permitted-data demo evidence. No access-control or deletion regression is acceptable. Use fakes for routine tests; mark fake output visibly and isolate its indexes. Actual Qwen3 answers may be described as demonstrated only after a real-model run; if local resources cannot support it, mark that evidence pending.

Maintain a tuning set separate from a frozen real-model evaluation set. Before a quality-certified release, use at least 100 cases (80 answerable, 20 unsupported): target at least 90% supported-answer success, 95% unsupported abstention and valid authorized references for every displayed citation. These are proposed acceptance targets, not measured results. Identifier validation alone does not prove semantic correctness.

Future production signoff additionally requires concrete workload/SLOs and budget, target-platform/GPU integration, security checks, capacity/fault tests, monitored rollout/rollback and timed restore. Proposed recovery targets are RPO 1 hour/RTO 4 hours, unverified until measured. Missing GPU/HA evidence does not block local implementation; it prevents corresponding production claims.

## 5. Boundaries

Included: selected-stack RAG, PostgreSQL metadata, private multi-user documents, durable jobs, source citations, bounded retained results, authorization, deletion/recovery, local tests and hardware-neutral application interfaces.

Excluded initially: OCR, reliable complex chart/table reconstruction, shared workspaces, semantic duplicate detection, persistent conversational memory, autonomous agents and fine-tuning. Docker packaging is planned during development; cloud provisioning, CI/CD deployment stages, Terraform/Helm configuration and GPU sizing are added when staging/production is needed. No paid AI API or infrastructure purchase is required now.

The future **1,000–5,000 RPS** objective remains a design target. It is not the number of users, a laptop capability or an achieved answer rate. Production workload, latency, providers, resource counts and costs are decided before deployment and tested; they need not be guessed before coding.
