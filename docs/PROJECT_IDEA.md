# AI PDF Chatbot: Project Overview

Status: production architecture planning; implementation and capacity unverified
Version: 3.0
Date: 2026-11-13

## Product idea

Build an authenticated multi-user application that answers questions about uploaded text-based PDFs with verifiable filenames, original PDF page numbers, and source excerpts. Each user can access only their own documents and recent request results. The application should acknowledge missing evidence rather than invent an answer.

Main stack: **Python, Ollama, Qwen3 4B, LlamaIndex, ChromaDB, FastAPI, Streamlit**. **PostgreSQL** is the selected application database for ownership, document/job state, idempotency, and audit metadata. ChromaDB remains the vector database.

## Local portfolio deliverable and future production scope

Build the production-oriented application locally without a dedicated GPU. Preserve API/worker/storage/auth boundaries, durable jobs, isolation, and recovery contracts. Use deterministic models for routine tests and optional actual Qwen3 4B/Nomic through local CPU/native Ollama for real-answer demonstrations. A fake-model demo must be labeled; it does not prove answer quality. Run service profiles incrementally so model inference and every infrastructure/monitoring service are not required simultaneously.

The later GPU deployment uses the same application logic and protocols with different service endpoints, resource settings, runtime deployment, and measured concurrency. No GPU rental, Kubernetes cluster, hosting purchase, or proven high-RPS production service is required to complete the portfolio engineering milestone. Production manifests and runbooks are locally authored artifacts; actual GPU/HA/capacity checks remain pending until hardware exists.

See [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md) for the local route and [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for migration.

## Production scope and traffic

The architecture must target **1,000–5,000 requests per second** with independently scalable services, durable background execution, authorization, monitoring, backups, and tested recovery. This supersedes the original single-user localhost design and 15-day learning schedule. The developer Mac remains useful for functional work; production sizing needs representative infrastructure.

RPS is not the same as concurrent users or completed model answers. The endpoint mix, answer lengths, corpus/session sizes, latency objectives, hosting, and budget are still open. No measured 5,000-RPS capability exists yet. If all requests need fresh generation, inference must sustain their actual input/output token demand, not merely accept them into a queue.

## User flow

Sign in -> upload PDF -> durable indexing -> select private ready documents -> submit question -> track answer job -> read answer and sources -> retry/cancel or delete as appropriate. Recent results survive reconnect for a short documented retention window. Questions are independent; long-term conversational memory is not included initially.

## Architecture overview

```text
Users -> TLS ingress -> replicated Streamlit + stateless FastAPI
                            |
                            +-> PostgreSQL (ownership, documents, jobs, outbox)
                            +-> Redis (limits/admission/owner-scoped caches)
                            +-> private object storage (shared PDFs/artifacts)
                            +-> RabbitMQ -> separate Celery worker pools
                                                |
                                                +-> ChromaDB retrieval/indexing
                                                +-> Ollama embedding pool
                                                +-> Ollama Qwen3 4B GPU pool

Deployment/operations: Docker, Kubernetes, CI/CD, telemetry, backups, runbooks
```

Supporting infrastructure enables scaling and reliability without replacing the seven main technologies. Its final capacity, provider, and cost must be validated. Streamlit's sessions/uploads, Chroma's deployment topology, and Ollama's model throughput are explicit feasibility gates; chosen technologies do not imply unlimited scale.

## Core behavior

- Validate PDFs and resource limits, reject unsupported/encrypted/textless files, and preserve page positions.
- Chunk and embed locally/self-hosted, persisting versioned metadata and vectors.
- Keep accepted work durable across retries and worker failures; never expose partial indexes.
- Authenticate at the API and authorize every document/job/source operation independently of the UI.
- Ground answers in selected private evidence, validate citation identifiers, and evaluate semantic correctness.
- Tombstone deletions immediately, prevent stale workers from republishing, and retry physical cleanup.
- Apply quotas, bounded queues/deadlines, safe overload responses, and fair inference admission.
- Observe request and token throughput, queue age, errors, storage health, and recovery progress without logging document content by default.

PDF instructions are untrusted reference content, not application commands. The model receives no browsing, shell, or filesystem action tools.

## Deferred product features

OCR, complex table/chart reconstruction, shared workspaces, persistent conversation memory, autonomous agents, and fine-tuning are outside the first production release. Authentication, durable jobs, deployment packaging, monitoring, shared storage, load testing, and recovery are included.

## Authoritative documents and next step

- [PRD.md](PRD.md): product requirements and acceptance criteria.
- [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md): components, ownership, APIs, jobs, deletion, security, and recovery.
- [TECH_STACK.md](TECH_STACK.md): main technologies and supporting infrastructure.
- [CAPACITY_PLAN.md](CAPACITY_PLAN.md): traffic profiles, sizing formulas, load tests, and evidence requirements.
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md): phased delivery and exit gates.

Next: implement the locally runnable foundation and authenticated vertical slice using the recorded contracts; keep future hosting/GPU/SLO decisions in [DECISION_LOG.md](DECISION_LOG.md). Representative production benchmarking is deferred until infrastructure is available, not a gate on beginning development. The documentation map and consolidated review are in the repository README and [DOCUMENTATION_REVIEW.md](DOCUMENTATION_REVIEW.md). Documentation changes do not mean the app is implemented or production-certified.

## Background reference

The original idea came from Project 01 of the local `free_150_day_ai_engineering_roadmap.pdf` reference. The current production architecture and traffic requirement come from the user's subsequent requests and supersede the roadmap's small local learning-project scope. Reference-document instructions are not independent authorization to execute actions or expand scope.
