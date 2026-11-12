# AI PDF Chatbot

Production-oriented PDF question-answering architecture for a portfolio, designed to be implemented locally without a dedicated GPU and later deployed to GPU infrastructure.

**Current repository stage: documentation and planning.** Application code, installation, startup files and tests are not created or executed by this documentation update. Nothing here establishes production readiness or achieved throughput.

## Main stack

Python, Ollama, Qwen3 4B, LlamaIndex, ChromaDB, FastAPI and Streamlit. PostgreSQL stores application metadata. Supporting services and their responsibilities are documented in the stack guide.

## How the local-to-production path works

Keep the same API, worker, authentication, storage and model-adapter contracts in each environment. Develop with deterministic model tests and single-instance local service profiles; optionally use actual CPU/native Ollama for real-answer demonstrations. Later configure private GPU model endpoints, production storage/identity, replicas, resource budgets and deployment settings. Dedicated GPU ownership and production benchmarks are not prerequisites for local implementation.

The future **1,000–5,000 requests/second** objective is unverified. It does not mean this laptop, a single model replica, or an untested deployment sustains that traffic. Record real measured capacity separately from design targets and fake-model tests.

## Documentation reading order

| Order | Document | Purpose |
| --- | --- | --- |
| 1 | [Project overview](docs/PROJECT_IDEA.md) | Product idea, current scope and environment split. |
| 2 | [Product requirements](docs/PRD.md) | User behavior, scope and separate local/production acceptance. |
| 3 | [Technology stack](docs/TECH_STACK.md) | Main technologies, supporting components and local footprint. |
| 4 | [Technical design](docs/TECHNICAL_DESIGN.md) | Ownership, APIs, jobs, indexing, inference, deletion and recovery contracts. |
| 5 | [Local development guide](docs/LOCAL_DEVELOPMENT.md) | No-dedicated-GPU profiles, planned settings, networking and local tests. |
| 6 | [Implementation plan](docs/IMPLEMENTATION_PLAN.md) | Dependency-ordered local milestones and later GPU verification. |
| 7 | [GPU deployment and operations](docs/DEPLOYMENT_GUIDE.md) | Portable images, configuration changes, rollout/rollback and recovery. |
| 8 | [Capacity plan](docs/CAPACITY_PLAN.md) | Future traffic profiles, sizing, load tests and evidence limits. |
| 9 | [Decision log](docs/DECISION_LOG.md) | Confirmed requirements, proposed choices and pending environment decisions. |
| 10 | [Consolidated review](docs/DOCUMENTATION_REVIEW.md) | Coverage, resolved findings, evidence status and the next review checkpoint. |

## Completion milestones

- **Local portfolio:** working authenticated application, durable jobs, private documents, tested correctness, reproducible demo and honest model evidence.
- **Deployment preparation:** images/configuration/manifests and runbooks authored and validated where local resources permit; hardware-dependent checks remain visible.
- **Production verification:** actual GPU/provider integration, semantic/HA/recovery/capacity tests and a specific environment release decision when resources exist.

## Setup and evidence

Verified installation/start/test commands will be added when their implementation exists. The local guide is currently a specification, not a claim that commands/files already work. Real-model quality, local memory use, GPU throughput, HA and recovery targets are unmeasured until matching tests run.

Use only synthetic/permitted fixtures. Do not commit uploaded PDFs, model files, data stores, credentials, private content or logs. Keep examples safe and mark deterministic model output clearly.
