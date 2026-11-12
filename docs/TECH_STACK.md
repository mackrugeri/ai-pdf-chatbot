# Technology Stack: AI PDF Chatbot

Status: production architecture choices; installation and capacity unverified
Version: 3.0
Date: 2026-11-13

## 1. Main stack

**Python, Ollama, Qwen3 4B, LlamaIndex, ChromaDB, FastAPI, Streamlit.** These remain the user-selected main technologies. PostgreSQL replaces SQLite for application metadata. The production target is 1,000–5,000 RPS, subject to the workload and evidence in [CAPACITY_PLAN.md](CAPACITY_PLAN.md).

| Main technology | Responsibility | Production boundary |
| --- | --- | --- |
| Python | API, processing, workers, and service code | Lock a tested supported version and dependency set. |
| Ollama | Serve self-hosted models | Private replicated inference endpoints with measured per-instance admission limits. |
| Qwen3 4B | Generate evidence-grounded answers | Pin tested model identity and quantization; size GPU replicas from token throughput and latency measurements. |
| LlamaIndex | RAG adapters and pipeline integration | No ownership decisions or uncontrolled parallel model calls hidden in adapters. |
| ChromaDB | Vector search and indexed excerpts | Use a private service/distributed deployment validated against corpus, write rate, HA needs, and retrieval QPS; no per-API embedded indexes. |
| FastAPI | Authenticated document, job, and chat API | Stateless replicas behind ingress; no ingestion/generation in API background tasks. |
| Streamlit | User-facing document and chat interface | Replicas with WebSocket/session affinity; benchmark sessions, reruns, polling, uploads, and reconnect behavior. |

Current deliverable: build/test this architecture locally without a dedicated GPU for a portfolio, with a configuration-driven path to later GPU deployment. Native/CPU Ollama, deterministic test models, single service replicas, and small fixtures are supported. No paid infrastructure or full production fleet is required locally. [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md) defines environment parity and [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) defines the future GPU transition.

A main-stack selection is not a throughput guarantee. No component replacement is authorized by a failed benchmark alone; record the result and review the change with the project owner.

## 2. Supporting production infrastructure

These are proposed supporting choices needed to implement the architecture; they do not change the main stack. Final provider, instance types, versions, and costs require measured sizing.

| Component | Proposed choice | Purpose |
| --- | --- | --- |
| Application database | PostgreSQL + Psycopg 3 | Authoritative ownership, document state, job/results, idempotency, audit metadata, and transactional outbox. |
| Connection management | PgBouncer plus bounded application pools | Keep replica/worker connections within the database connection budget; verify compatibility of chosen pooling mode. |
| Durable jobs | Celery + RabbitMQ quorum queues | Separate ingestion, answer, and cleanup queues; publisher confirms, redelivery, retry limits, and reconciliation. PostgreSQL remains the job source of truth. |
| Fast shared state | Redis | Distributed quotas, short-lived admission counters, and owner/version-scoped caches; not the only copy of accepted jobs or results. |
| Shared files and payloads | S3-compatible private object storage | PDFs, bounded job/result payloads, and artifacts across replicas; version-pinned verified staging, server-only immutable final objects, encryption, lifecycle cleanup, and backups. No pod-local authoritative uploads. |
| Deletion recovery journal | Independently protected append-only object-storage namespace or equivalent durable service | Minimal deletion intents survive an application database rollback; restricted retention and verified replay/cutover gate restored access. Provider guarantees must be validated. |
| Identity | OIDC/OAuth2 provider integration | Authenticate users and issue access tokens scoped/audienced for FastAPI; verify a concrete provider before release. |
| Traffic management | TLS load balancer / Kubernetes ingress | Route HTTP/WebSockets, enforce limits, protect private services, and preserve Streamlit affinity. |
| Packaging | Docker | Build immutable, scanned API/UI/worker images. |
| Production orchestration | Kubernetes with Helm deployment templates | Replicas, probes, rolling releases, resource budgets, disruption policies, and independently scalable worker/GPU pools. |
| Local integration | Docker Compose | Reproduce service contracts at small scale; not evidence of production throughput. Native Ollama can remain on the developer Mac. |
| Telemetry | OpenTelemetry, Prometheus, Grafana | Sanitized traces, metrics, capacity dashboards, and alerts with controlled telemetry access. |
| Delivery | GitHub Actions | Checks, image scans, staging deployment, migrations, and gated release/rollback workflow. |
| Load verification | k6 or Locust (select one during setup) | Open-loop offered-load tests and separate browser/WebSocket tests; avoid coordinated omission. |

PostgreSQL, the broker, Redis, object storage, the independent deletion journal, and the selected Chroma deployment need documented HA/recovery arrangements. Job history partitioning, idempotency receipts, external payload retention, and cleanup throughput must satisfy the measured storage budget. Multiple application replicas alone do not provide end-to-end HA.

## 3. Supporting Python dependencies

Use uv with a project virtual environment and committed `pyproject.toml`/`uv.lock`. Verify the Python target against all selected dependencies before locking it. Needed groups include FastAPI/Uvicorn, Pydantic/configuration, HTTPX, multipart support, PyMuPDF, LlamaIndex adapters, Chroma client, Psycopg/pooling, Celery, Redis client, object-store SDK, supported token validation, metrics/tracing, pytest, and Ruff. Use versioned SQL migrations executed as a release task; an ORM is not required by this plan.

Nomic Embed Text through Ollama is the supporting embedding model. Use the same immutable embedding identity for indexing and questions; verify dimensions and prevent silent truncation. Embedding capacity is sized separately from generation. Check PyMuPDF and all model/dependency licenses before distribution. Do not invent package pins until the integration is tested.

## 4. Models and scaling

Pin Qwen3 4B and embedding artifacts/digests, model-server image/version, tokenizer, quantization, context/output limits, and index fingerprint. Preload/warm replicas before readiness; never download models on an end-user request. Benchmark GPU memory, prompt prefill, decode, and mixed workloads with realistic lengths. Use separate embedding and generation pools in production, and reserve query-embedding capacity separately from bulk ingestion (dedicated endpoints or a guaranteed-capacity scheduler). A single local endpoint serializes model calls and schedules query versus ingestion work at bounded batch boundaries.

Configure bounded per-endpoint concurrency and a scheduling layer that routes only within each replica's measured safe capacity. Adding API pods does not add tokens/second. Model-serving protocol adapters must remain isolated so a future runtime change can be reviewed without rewriting document ownership and RAG services.

## 5. Security and configuration

Configure database/broker/Redis/object-store endpoints, OIDC issuer/audience/JWKS, model endpoint inventory, quotas, queue budgets, token limits, job deadlines, retention, and telemetry using validated environment settings and secret references. Production startup must reject unsafe defaults, absent required secrets, deterministic fake models, test signing keys/issuers, and local-only journal/storage configurations. Local/test modes must be explicit and must not bypass ownership or token-validation logic. Commit only placeholder examples; do not store access tokens, content, credentials, dumps, or model artifacts in Git or container build contexts.

All storage and inference services are private. FastAPI validates access tokens independently of Streamlit and authorizes document/job IDs on every operation. Never trust an owner ID or plain identity header from the UI. Do not cache per-user data globally in Streamlit; keep state isolated and make critical results recoverable from the API.

## 6. What is deferred

| Deferred item | Reason |
| --- | --- |
| pgvector | PostgreSQL owns metadata; ChromaDB remains the chosen vector system. |
| React / Next.js | Streamlit stays selected; its capacity is an explicit release gate. |
| Agents / LangGraph | Controlled RAG meets current product scope. |
| Cloud model APIs | Self-hosted models remain selected; no silent fallback. |
| OCR / complex table reconstruction | Separate product scope and resource/security evaluation. |
| Reranking / hybrid search | Add only for evaluated retrieval failures, then remeasure latency and capacity. |
| Multi-region active-active | Requires a separate consistency and cost design after the initial production deployment. |

Docker, durable job infrastructure, authentication, monitoring, shared storage, load tests, and deployment automation are **not deferred** in this production baseline.

### Local footprint versus future infrastructure

Run only the profiles needed for the current milestone. PostgreSQL, RabbitMQ, Redis, a private S3-compatible local service, and a Chroma service have single-instance local equivalents; the exact local object-store implementation must pass versioning/checksum/access-policy contract tests. Native Ollama is outside the Compose network on a developer Mac; container-to-host connectivity must be explicitly configured and tested. Use a local OIDC provider for authenticated end-to-end tests; deterministic signed test tokens are limited to isolated automated tests using the same validation path.

PgBouncer, Kubernetes, HA replicas, dedicated GPU pools, full dashboards, and distributed Chroma are production topology or optional local integration profiles. Their manifests/configuration can be authored locally without provisioning them. Do not require all profiles, both models, and all observability services to fit in memory at once. Functional development remains possible through deterministic fakes when real models do not fit. Model licenses and real-output claims still require actual model verification.

## 7. Evidence and change control

Record tested versions, provider configuration, licenses, dependency scans, model identities, and measured component capacities before release. Update the PRD, TDD, implementation plan, and capacity plan for incompatible changes. Rebuild/version indexes for embedding/chunking changes; never mix incompatible vectors.

Official references reviewed for this design: [Streamlit architecture](https://docs.streamlit.io/develop/concepts/architecture/architecture), [Streamlit authentication](https://docs.streamlit.io/develop/concepts/connections/authentication), [Streamlit caching](https://docs.streamlit.io/develop/concepts/architecture/caching), [Chroma distributed architecture](https://docs.trychroma.com/reference/architecture/distributed), [Ollama FAQ](https://docs.ollama.com/faq), [Celery with RabbitMQ](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/rabbitmq.html), and [Kubernetes autoscaling](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/). Verify exact selected versions against these sources during implementation.
