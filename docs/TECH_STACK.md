# Technology Stack

Version 4.0 | 2026-11-13 | Selected design; versions/installation unverified

## 1. Fixed main stack

| Technology | Responsibility |
| --- | --- |
| Python | Application, processing and service code. |
| Ollama | Local/CPU development and GPU-hosted model serving through the same HTTP adapter. |
| Qwen3 4B | Evidence-grounded answer generation. |
| LlamaIndex | RAG/chunking/retrieval integrations under application-owned contracts. |
| ChromaDB | Versioned vectors/excerpts; private service, not independent embedded indexes per API replica. |
| FastAPI | Authenticated, versioned document/job/chat API. |
| Streamlit | Upload, document management, chat and source UI. |

**PostgreSQL** is the fixed application database for ownership, document/job state, idempotency and outbox records. ChromaDB remains vector storage; pgvector is not part of this design.

## 2. Supporting components

| Choice | Purpose / timing |
| --- | --- |
| uv, virtual environment, lockfile | Reproducible Python setup from the foundation phase. |
| Nomic Embed Text via Ollama | Same pinned embedding identity for documents and questions. |
| PyMuPDF | Page-level PDF text extraction; review licensing before distribution. |
| Pydantic/settings, Uvicorn, HTTPX | Validated schemas/configuration, API serving and bounded local/private HTTP calls. |
| Psycopg 3, bounded pools, versioned SQL migrations | PostgreSQL access and controlled schema changes; no ORM required. |
| Celery + RabbitMQ | Separate durable ingestion/answer/cleanup queues. PostgreSQL is authoritative, broker delivery at least once. |
| Redis | Shared admission/quotas and scoped caches; never sole durable job storage. |
| Private S3-compatible object service | PDFs, immutable artifacts and bounded job/result payloads; local implementation must pass version/checksum/policy tests. |
| OIDC/OAuth2 provider | Login plus API-audience access tokens; use a local provider for end-to-end development, same validation path later. |
| Docker + Compose | Portable images and incrementally runnable local service profiles. Native Ollama can remain outside Compose. |
| pytest, Ruff, Git/GitHub | Tests, formatting/linting and version control. |

Provider/version choices are foundation integration details or later deployment decisions, not permission to replace the fixed main stack. Pin tested packages/images/models and record compatibility/licenses during setup; avoid invented version numbers before installation.

## 3. Later environment infrastructure

When staging/production is required, add TLS/WebSocket-aware ingress, PostgreSQL connection pooling/HA, independently protected deletion journal, production object-storage policies, reserved query embedding and GPU generation pools, and a supported Chroma scale topology. Deployment tooling is **GitHub Actions** for CI/CD, **Terraform** for provisioned infrastructure where applicable, and **Kubernetes/Helm** for the scale topology. Monitoring uses sanitized OpenTelemetry/Prometheus/Grafana integrations as needed; full dashboards and production HA are not local startup prerequisites.

Keep endpoints, credentials, timeouts, replicas and resource budgets in validated configuration/infrastructure files. No CUDA/device-specific logic belongs in PDF/RAG/API services. Production rejects fakes, test identities/default secrets and local-only recovery assumptions. All private services stay off the public internet.

## 4. Local constraints and deferred features

Start single-instance dependencies only when needed, serialize real model operations, and use deterministic model adapters for routine tests. CPU/native Ollama is optional for actual semantic checks; no dedicated GPU is required to build the application. Fake and real embeddings require separate index namespaces. Never substitute a smaller answer model or a remote API silently.

React/Next.js, agents, OCR, fine-tuning, rerankers/hybrid search and multi-region active-active are deferred. Preserve the fixed main stack unless a measured incompatibility leads to an explicit owner-approved change. See the [technical design](TECHNICAL_DESIGN.md) for contracts and the [implementation plan](IMPLEMENTATION_PLAN.md) for tasks.
