# Architecture Decisions and Open Choices

Status: planning baseline; choices are not evidence of installation or performance
Version: 1.0
Date: 2026-11-13

## 1. How to use this log

The project owner/developer owns each decision initially. Record a date, rationale, affected contracts, evidence, and replacement decision when implementation changes a choice. User-confirmed requirements take precedence over a supporting technology proposal. A future production decision marked pending does not block the local portfolio milestone unless explicitly noted.

## 2. Confirmed requirements

| Decision | Status | Rationale / consequence |
| --- | --- | --- |
| Main stack: Python, Ollama, Qwen3 4B, LlamaIndex, ChromaDB, FastAPI, Streamlit | User confirmed | Preserve these technologies; request an explicit change if evidence reveals a blocker. |
| PostgreSQL for application metadata | User confirmed | No SQLite application metadata; Chroma remains vector storage. |
| Production-oriented architecture for a portfolio | User confirmed | Implement durable jobs, identity/isolation, service boundaries, recoverability and deployment artifacts locally. |
| Local development without a dedicated GPU | User confirmed | Fakes/CPU/native model options, staged local services, no paid GPU prerequisites. |
| Future 1,000–5,000 RPS objective | User confirmed as design target | Not a local requirement or achieved-capacity claim; workload-specific proof is future work. |
| No code/GPU deployment provisioned by documentation work | Current scope | Writing files does not install services, create cloud resources or certify readiness. |

## 3. Architectural baseline

| Choice | Status | Reason and verification |
| --- | --- | --- |
| Same application ports/contracts across local and GPU environments | Adopted design | Model/storage/network/resource configuration varies, not ownership/lifecycle/RAG logic. Verify adapter contract tests and migration smoke. |
| Separate API, UI and durable worker roles | Adopted design | Keep slow parsing/inference out of API request processes. Locally use single replicas. |
| PostgreSQL authoritative state + transactional outbox | Adopted design | Prevent accepted job state from depending solely on broker delivery. Test publication crashes/reconciliation. |
| Celery/RabbitMQ, Redis, private object storage | Proposed supporting implementation | Validate locally against durable delivery, admission, checksum/versioning and access contracts. No install/version/provider is implied. |
| Attempt-isolated vector and result artifacts | Adopted design | DB fencing alone cannot prevent stale external writes. Publish exact winner and isolate loser cleanup. |
| Query embedding reservations separate from ingestion | Adopted design | Generation/embedding separation alone cannot protect query latency. Local scheduler, later reserved pools. |
| Immutable verified upload identity | Adopted design | Prevent mutable presigned targets from changing accepted bytes. |
| Independent deletion journal + closed restore | Adopted design | Prevent deletion resurrection after rolling back application data. Local same-disk model cannot prove independent durability. |
| Short-lived reconnect results, independent idempotency receipts | Adopted design | Recover sessions without retaining indefinite chat history or recreating expired work. |
| Kubernetes/Helm for later scale topology; Compose for local | Proposed deployment choice | Author/render locally; real scheduling/HA is pending deployment evidence, not required for local work. |

## 4. Choices needed early in implementation

| Decision | Required by | How to close |
| --- | --- | --- |
| Supported Python/package/image versions | Foundation | Test native dependencies/platform compatibility, review licenses and commit lockfile. |
| Local S3-compatible implementation | Upload integration | Pass checksum, version pinning, immutable promotion, policy and cleanup contract tests. |
| Local OIDC provider/token integration | Authenticated vertical slice | Exercise actual login/access-token issuer/audience, expiry, logout and backend validation. No unguarded production bypass. |
| Partition/lookup/global uniqueness strategy | Persistence/retention implementation | Migration/integration tests plus measured local data layout; keep active jobs and receipts safe. |
| Exact settings/commands/local footprint | Reproducible handoff | Implement declared settings and replace planned workflows with tested commands. |
| Model identity and feasible local real run | Real-model demo | Record actual artifacts, memory, latency and quality, or explicitly mark real evidence pending. |

## 5. Future production-only decisions

Required before production verification, not before local coding: actual traffic mix and token/corpus/session/upload distributions; latency/error/availability SLOs; provider/region and GPU/resource budget; measured per-component capacities; model replica/headroom plan; production identity provider; private object storage and independent journal durability/retention/cutover; supported Chroma deployment; HA/failover topology; retention/storage/cleanup budgets; operational owners and environment-specific release approval.

Do not guess values just to close this list. Until resources exist, leave these marked pending and retain sizing formulas/manifests as proposals. Any component replacement needs a recorded rationale and owner approval. See [CAPACITY_PLAN.md](CAPACITY_PLAN.md) and [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).
