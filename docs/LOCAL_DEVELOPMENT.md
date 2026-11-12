# Local Development Without a Dedicated GPU

Status: implementation specification; startup files and application code are not yet present
Version: 1.0
Date: 2026-11-13

## 1. Goal

Develop and demonstrate the production-oriented architecture on the existing computer without buying/renting GPU infrastructure. Preserve the same application contracts for a later GPU-hosted deployment. A single replica is a deployment choice, not permission to remove authentication, job durability, ownership filtering, or recovery logic.

Main stack remains Python, Ollama, Qwen3 4B, LlamaIndex, ChromaDB, FastAPI, Streamlit; PostgreSQL owns application metadata. No package, model, service, or performance capability is assumed installed/verified merely because it appears in the plan.

## 2. Local operating profiles

| Profile | Services and model mode | What it proves |
| --- | --- | --- |
| Unit/contract tests | Python services with deterministic model/storage fakes and isolated fixtures | Schemas, state transitions, prompt/citation handling, ownership, timeout/error paths; no model-quality claim. |
| Local integration | Single-instance PostgreSQL, RabbitMQ, Redis, S3-compatible service, Chroma, API, worker processes; local OIDC provider when exercising login; deterministic model adapter | Real storage/job/auth boundaries, retries, duplicate delivery, deletion and reconnect. Start subsets for component tests, then a bounded full vertical slice. |
| Local real-model demo | Same application contracts; native or CPU-capable Ollama serving pinned Qwen3 4B and Nomic, with strictly serialized model work | Genuine local answers/embeddings, citation inspection, measured local latency and semantic quality. No production throughput proof. |
| Local operations exercises | Integration profile plus selected dashboards, second API replica, restore/failure tooling as needed | Single-machine recovery, affinity, metrics, draining, and replica simulations; no multi-host HA proof. |
| Future GPU staging | Production deployment resources and real GPU model endpoints | Hardware/model compatibility, real concurrency/quality parity, later production performance evidence. Not required now. |

All test modes must be explicit and visible in UI/results/evaluation reports. Production configuration rejects deterministic model fakes, test issuers/signing keys, local test credentials and namespaces. Fakes never act as an automatic fallback for a failed real-model request.

## 3. Resource strategy

Do not start a GPU cluster or every production service replica locally. Begin with unit tests; bring up only the real dependencies needed for the current integration test. For a user-facing vertical slice, use single instances and measured container limits. Keep full tracing/dashboard stacks and HA replicas optional.

For real model runs, begin with one global model-operation slot, small page-aware batches, small fixtures and conservative context. Do not load both models unnecessarily; let the scheduler switch/unload them where supported. A shared local embedding endpoint schedules query versus ingestion queues at bounded batch boundaries. Record memory pressure, latency, and failures before increasing limits.

CPU-only inference is permitted and may be slow. Native acceleration, if available, is optional; a discrete NVIDIA GPU/CUDA is not a local prerequisite. If the selected model cannot run within available memory, continue all deterministic/integration work and mark real-model evidence pending. Do not silently replace Qwen3 4B, change embedding dimensions, or claim semantic evaluation from mocks.

The official [Ollama Docker guide](https://docs.ollama.com/docker) documents CPU-only and GPU configurations. The [Ollama FAQ](https://docs.ollama.com/faq) documents host binding and runtime limits. Verify settings for the pinned runtime during setup.

## 4. Environment contract

The following names are planned configuration contracts to implement in typed settings and `.env.example`; they are not existing executable setup instructions.

| Setting | Local behavior | Future production behavior |
| --- | --- | --- |
| `APP_ENV` | Explicit `development` or `test` | `production`; reject unsafe/test settings. |
| `MODEL_BACKEND` | Explicit `fake` for deterministic work or `ollama` for real inference | `ollama`; fake forbidden. |
| `OLLAMA_GENERATION_URL` | Native host/CPU-service URL | Private model-router/generation-pool URL. |
| `OLLAMA_QUERY_EMBEDDING_URL` | May share one serialized local endpoint | Reserved query embedding pool or guaranteed-capacity route. |
| `OLLAMA_INGESTION_EMBEDDING_URL` | Same endpoint allowed with scheduler limits | Independently budgeted ingestion embedding route. |
| `GENERATION_MODEL` / `EMBEDDING_MODEL` | Pinned Qwen3/Nomic identities | Same logical identities unless an explicit model/index migration is evaluated. |
| `DATABASE_URL` | Dedicated local application/test PostgreSQL database | Private database endpoint through tested pooler settings. |
| `BROKER_URL` / `REDIS_URL` | Local service network | Private HA service endpoints with credentials/TLS as required. |
| `OBJECT_STORAGE_ENDPOINT` | Versioning-capable local S3-compatible service | Private production object service. |
| `OBJECT_STORAGE_BUCKET` | Isolated development/test bucket | Private application bucket with tested policies. |
| `DELETION_JOURNAL_ENDPOINT` / `DELETION_JOURNAL_BUCKET` | Separate namespace/credentials, with explicitly simulated independent durability | Independently protected account/service outside application restore boundary. |
| `OIDC_ISSUER` / `OIDC_AUDIENCE` | Local OIDC provider; isolated signed-token fixtures only for automated tests | Selected real provider/audience, strict validation. |

Additional pool, retention, timeouts, queue/admission, TLS, object credentials, model digest and artifact settings must be declared once in configuration and referenced by both API and workers. Secrets use placeholders in examples and private local secret files; they never enter images, commits, logs, or model prompts.

### Host/container networking

A container cannot reach native host Ollama by assuming its own localhost is the host. Implement and document an explicit configurable host gateway for the developer platform, or use the CPU Ollama service on the Compose network. Do not assume Docker-on-Mac GPU passthrough/CUDA support. Bind native services conservatively and expose only the interfaces needed for private local access. Production does not reuse a developer host address.

## 5. Keep local and production behavior aligned

- Model ports/adapters hide hardware; business logic must not branch on CPU versus GPU.
- Tests and real inference have different model/index fingerprints and isolated database/object/vector namespaces. Never query real vectors with fake query embeddings.
- Storage adapters use actual checksums/version identities, immutable completion, ownership checks, and attempt-isolated artifacts, including on local single replicas.
- Real RabbitMQ/outbox integration is tested even when routine unit tests use fakes. API in-process background tasks are not a substitute for durable jobs.
- Local authentication runs through the same token-validation/ownership path. No universal hardcoded user or unguarded production route is permitted.
- Single-machine tests demonstrate semantics, not independent failure domains. A separate local journal bucket models the contract but cannot survive complete laptop loss independently.

## 6. Planned startup and teardown workflow

Application code, Compose files and verified commands will be created during implementation. Do not present nonexistent commands as working setup.

1. Verify/install the chosen supported Python, uv, Git and Docker/Compose; add Ollama only for real-model work.
2. Generate private development secrets and isolated storage/database namespaces from safe examples.
3. Start the required local dependency profile, wait for readiness, and apply versioned migrations explicitly.
4. Start API, outbox/reconciliation and the required worker queues; start local identity provider/UI for user-flow testing.
5. Select fake or real model mode explicitly. For real mode download pinned models ahead of requests, verify model readiness, and record identities.
6. Upload a small permitted PDF, authenticate as two users, verify private answering, reconnect/job discovery, cancellation and deletion.
7. Stop/restart a worker and verify accepted work recovers; inspect sanitized logs/metrics.
8. Shut services down without deleting persistent data by default. Destructive reset requires an explicit development-only target and cannot point at production endpoints.

During implementation, replace this workflow with tested platform-specific README commands, estimated resource use and troubleshooting. Installation and service configuration are later implementation actions, not performed by this document.

## 7. Required local checks

| Area | Minimum check |
| --- | --- |
| PDF | Invalid/encrypted/textless/oversized input; original page numbering; chunk progress. |
| Identity | Missing/forged/wrong-audience tokens; owner isolation; user deactivation; session/token expiry. |
| Upload | URL reuse/overwrite races; verified immutable version; duplicate completion; quota reservation/release. |
| Jobs | Outbox crash; duplicate broker delivery; worker death; cancellation; retry/deadline behavior. |
| Vectors | Stale worker resumes after successful retry; only winning attempt is searchable; loser cleanup cannot delete winner. |
| Scheduling | Ingestion flood cannot consume every query-embedding slot; local serialization remains bounded/fair. |
| Reconnect | Empty UI session rediscovers only the signed-in user's recent jobs; cursor/expiry cases. |
| Deletion | In-flight work cannot republish deleted data; remove applicable object versions and result payloads. |
| Recovery | Restore an older application backup with newer journal intents; missing journal blocks opening access. |
| Retention | Active inputs survive waiting/running; terminal result expiry preserves idempotency receipts. |
| Observability | Correlation and useful errors exist without logging prompts, tokens, private excerpts, or secrets. |

Routine tests do not require a model download. An opt-in real-model test suite uses actual Ollama, records hardware/model/configuration, and is never reported as passed when skipped. Fault/real-storage tests need isolated stores; no destructive tests run against normal development or production data.

## 8. Portfolio evidence

Ship a reproducible local demo, architecture/service diagrams, tests with recorded outcomes, example API contracts, deployment templates, limitations, and a short demonstration using permitted PDFs. Label every result with fake/real mode and actual environment. Use the 100-case frozen evaluation for a real semantic report; until run, mark it pending.

Appropriate claim: production-oriented architecture, locally implemented/tested, with configuration-driven GPU deployment and an unverified future 1,000–5,000 RPS target. Avoid claims of production readiness, zero-downtime HA, or achieved RPS without matching evidence. The [documentation review](DOCUMENTATION_REVIEW.md) provides the evidence checklist.
