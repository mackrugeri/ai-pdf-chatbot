# Technical Design: AI PDF Chatbot

Version 4.0 | 2026-11-13 | Architecture contract; implementation/capacity unverified

## 1. Architecture and local-to-GPU contract

```text
Browser -> Streamlit -> FastAPI
                          +-> PostgreSQL: owners, documents, jobs, receipts, outbox
                          +-> Redis: quotas/admission/scoped cache
                          +-> Private object storage: PDFs and payloads
                          +-> Outbox publisher -> RabbitMQ
                                                   +-> ingestion workers
                                                   +-> answer workers
                                                   +-> cleanup workers
Workers -> ChromaDB and model adapters -> Ollama (Qwen3 / Nomic)
```

API, UI, workers and storage/model adapters have separate responsibilities. API processes never perform long PDF parsing/generation in in-process background tasks. Queue messages carry job IDs; workers resolve authorized payload references from PostgreSQL. Durable files are not pod-local.

**Local requires no dedicated GPU.** Use single service replicas, deterministic model fakes for routine tests, and optional actual CPU/native Ollama for real answers. Start dependency profiles incrementally; do not require both models, HA replicas and all dashboards to fit at once. Share one serialized model-operation slot locally, with fair query/ingestion scheduling. A real-model demo requires an actual run; otherwise label semantic evidence pending.

**Later GPU staging/production uses the same application code/contracts.** Model/storage/network endpoints, credentials, timeouts, concurrency budgets, runtime devices and replicas are environment configuration. CI/CD, Terraform and deployment manifests implement those changes when needed; detailed provisioning instructions are not required now. No CPU/GPU branches or hardcoded host paths belong in domain logic. Hardware-only moves do not force reindexing; embedding/chunking identity changes do. Verify target-platform dependencies, model parity and performance before release; targeted compatibility/bottleneck changes can still be necessary, so zero future code changes cannot be guaranteed.

## 2. Configuration and interfaces

Typed settings define environment, explicit fake/Ollama backend, generation/query-embedding/ingestion-embedding endpoints, model identities, database/broker/Redis/object endpoints, OIDC issuer/audience, secrets, quotas, deadlines, retention and logging. Declare them once in `.env.example` and validate in API/workers. Production startup rejects fake models, test issuers/signing keys, placeholder secrets and local-only journal/storage defaults.

Model ports expose embeddings and structured answer generation; implement deterministic and Ollama adapters behind the same contracts. Isolate SDK-specific code in adapters. Keep fake/real model fingerprints and storage namespaces separate: fake query embeddings must never search real vectors. Container localhost is not the native host; document/test the configured host gateway or run CPU Ollama on the Compose network. Do not assume Mac CUDA/passthrough support.

Initial functional limits, tunable after measurement: 20 MiB/PDF, 300 pages, 2 million extracted characters, 2,000 question characters, 10 selected documents; page-bounded chunks around 1,200 characters/200 overlap; top 6 retrieval candidates; up to 4,000 context characters. Request an 8,192-token model context/1,024-token output only after verifying support. Count/bound the complete prompt with output headroom; character caps alone do not bound tokens. Start with a 180-second model timeout and one local model operation; record actual resource use before increasing limits.

## 3. Identity, ownership and private data

OIDC login must obtain access tokens for the API audience. FastAPI independently validates signature/allowed algorithm, issuer, audience, expiry and scopes, including key rotation; an ID token or plain owner header is insufficient. Map `(issuer, subject)` to an internal user and check active status. Use a local OIDC provider for end-to-end testing; isolated signed fixtures are for automated tests only, through the same validation path.

All document/job/source/download/retry/delete queries enforce the authenticated owner. Return uniform `404` for absent/inaccessible resources. Retrieval filters owner, selected ready version and published attempt, then verifies returned metadata. Cache keys include owner, published versions/attempts, model/index fingerprint and query/configuration; reauthorize before serving results. No global per-user Streamlit cache. Render content safely, clear session tokens/data on logout, and check expiry/deactivation. Public exposure is limited to authenticated ingress; databases, broker, vectors, storage and Ollama remain private.

PDF text is untrusted reference data. Delimit excerpts and prohibit source instructions from overriding application rules; no model action tools. Parse in network-disabled resource-limited subprocesses. Log request/job correlation, counts, timings and sanitized errors, not credentials, questions, excerpts, answers or model reasoning. Audit privileged operations without default content access.

## 4. Data and API contracts

PostgreSQL tables: `users`; owner-scoped `documents` with verified object identity/hash, counts, status and active version; `document_versions` with fingerprint and published attempt; `jobs` with owner/type/references, state, lease/heartbeat/deadline and result reference; transactional `outbox`; separate `idempotency_receipts`; minimal audit/deletion records. Timestamps are UTC; use UUIDs and owner/time/state indexes for bounded lookups. Enforce unique `(owner, hash)` for live duplicates and owner/endpoint/key receipts with request hashes. Use parameterized queries, bounded pools, explicit versioned SQL migrations and short transactions; no DB locks/connections across model/storage calls.

Chroma records carry owner/document/version/attempt IDs, deterministic chunk ID, original filename, original 1-based PDF page index and text. Object storage owns immutable PDFs/artifacts and encrypted bounded input/result payloads. Hot SQL rows contain control metadata/references, not repeated excerpts. Use generated private keys, checksums/version IDs, bounded access policies and short-lived authorized download URLs; previously issued URLs/bytes cannot be recalled instantly.

Protected API prefix `/api/v1`; Bearer access token on every data operation. Errors: `{error:{code,message,retryable},request_id}`. Require idempotency keys on create/complete/chat/retry operations; conflicting reuse returns `409`.

| Method / route | Contract |
| --- | --- |
| `GET /health/live`, `/health/ready` | Minimal public liveness; detailed readiness internal/operator-only, no expensive per-probe generation. |
| `GET /capabilities` | Sanitized authenticated availability and configured limits. |
| `POST /uploads` | `{filename,size_bytes}` -> `201` upload/document ID and expiring staging target. |
| `POST /uploads/{id}/complete` | Verify/freeze accepted bytes, enqueue -> `202`; owner duplicate may return `200`. |
| `GET /documents`, `/documents/{id}` | Owner list with keyset pagination, or bounded detail/status/errors. |
| `GET /documents/{id}/download` | Authorized expiring download target when enabled. |
| `POST /documents/{id}/retry` | Eligible failed ingestion -> `202`; requires intact original and compatible config. |
| `DELETE /documents/{id}` | Journal + tombstone + durable cleanup -> `202` deletion job, idempotent repeated status. |
| `POST /chat` | `{question,document_ids}` -> `202` answer job, not a completed answer. |
| `GET /jobs`, `/jobs/{id}` | Recent owner summaries/detail; only detail returns an authorized unexpired completed result. |
| `POST /jobs/{id}/cancel` | Durable idempotent cancellation, stopping work at safe checkpoints. |

All table routes except health are relative to the protected prefix. Lists return `{items,next_cursor}`, default limit 20/max 100; jobs allow state/type filters, ordered by `(created_at DESC,id DESC)`. Opaque cursors bind owner, filters and snapshot upper bound; ownership is also independently enforced. Job summaries expose ID/type/state/timestamps/expiry/result availability, never payloads. Reconnect rediscovers jobs without remembered UI IDs. Detail supports conditional reads; poll only active jobs with hints, backoff and jitter.

Chat result: `{answer,insufficient_evidence,sources:[{source_id,chunk_id,document_id,document_version,filename,page_number,excerpt}]}`. Document states: uploading/queued/processing/ready/failed/deleting/deleted. Job states: queued/running/retrying/succeeded/failed/cancelling/cancelled/expired. HTTP errors: `401` credentials, `403` operation scope, `404` absent/inaccessible, `409` state/index/idempotency conflict, `410` expired retained result, `413` size, `415` file type, `422` validation, `429` quotas, `503` dependency/capacity. Async failures appear as sanitized job errors, not changed submission responses.

## 5. Ingestion, retries and stale-worker safety

1. Reserve owner quota and issue staging-only upload access. At completion pin the exact object version, verify actual size/SHA-256 and promote only those bytes to a generated server-write-only final identity. Never verify one version then read/copy latest; final writes are create-only where supported.
2. Commit document/job/idempotency/outbox together after verified promotion. Duplicates are owner-scoped; release reservations and reconcile orphan/staging objects after crashes. URL reuse must not change indexed/downloaded bytes.
3. Outbox publishes persistent job IDs with broker confirms. Celery/RabbitMQ uses durable queues, bounded prefetch, tested late acknowledgments and capped retries; delivery is at least once, not exactly once. PostgreSQL owns acceptance/results.
4. Claim a lease with a fresh attempt namespace; validate/extract/chunk page-wise, retaining original page gaps, then embed bounded batches without silent truncation.
5. Write vectors/artifacts only within that attempt. Verify complete indexing and atomically publish its pointer only if lease/version/current document state permit. Retrieval accepts only the winner. A loser cannot overwrite/delete winner records: cleanup is scoped to its own attempt, never a broad version filter. Repeat orphan sweeps after stale writers terminate/lose access before declaring physical cleanup complete.
6. Heartbeats, deadlines, cancellation and capped backoff/jitter handle transient faults; invalid files fail permanently. Reconcile outbox/leases and replay safely after restart. Idempotency receipts outlive the client retry horizon, even after result payload expiry.

Separate ingestion, answer and cleanup queues. Reserve query-embedding capacity separately from ingestion (dedicated endpoints later or guaranteed scheduler shares); separating generation from embeddings alone is insufficient. Locally serialize work and schedule bounded ingestion batches with fairness both ways. Distributed admission limits measured per-endpoint capacity, owner quotas and queue depth/age; local semaphores alone cannot enforce cluster capacity. Redis/admission uncertainty closes new admission; accepted jobs remain durable. A timed-out model call with unknown execution must release capacity only after confirmed completion/cancellation or endpoint reset, not blind duplicate retries.

## 6. Answering and deletion

Resolve owner/ready versions/attempts, embed question, retrieve only allowed evidence and enforce full-prompt budgets. No selected documents means validation failure, never search all. Label supplied excerpts, ask for structured answer/source IDs/abstention, validate schema and inline references, resolve page metadata server-side, and allow one bounded format repair. No evidence gives deterministic abstention; invalid output becomes a job failure. Identifier checks do not prove factual support.

Recheck current access/state before publishing and serving answers. A deleted/revoked source invalidates the whole affected answer, not just its citation. Do not use conversation history for retrieval initially.

Deletion first durably appends an idempotent minimal intent to a journal protected outside the application DB restore boundary, then commits tombstones/cancellation/outbox; acknowledge only after both succeed. If the journal succeeds but DB fails, reconcile the intent conservatively. New reads exclude accepted deletions; in-flight bytes crossing the final check beforehand may finish. Cleanup removes applicable object versions/noncurrent versions/multipart remnants, vectors/attempts, saved answers and caches; delete markers alone do not erase bytes.

Restore keeps access/dispatch closed, fences old writers, restores stores and replays the current independent journal through a verified cutover checkpoint, including deletions newer than the backup. Missing coverage/replay keeps readiness closed. Protect journal history from normal roles and retain beyond all restorable backups plus recovery margin. A local separate bucket simulates the contract, not independent laptop-loss durability.

Finalize time partition boundaries/lookup routing and uniqueness constraints with migration tests; partitioning must preserve owner-scoped idempotency. Keep active inputs through terminal/recovery grace; proposed terminal-result TTL is 24 hours after completion, abandoned uploads 1 hour, sanitized logs/audit and backups 30 days. Finalize retention before production; journal retention is longer and independent. Keep receipts when payloads expire; use time-partitioned terminal history and bounded object/orphan cleanup without dropping active jobs or weakening global idempotency constraints. Old backups expire under the disclosed policy; deletion does not instantly erase them.

## 7. Future deployment and capacity

When needed, configure immutable target-platform images, real GPU Ollama endpoints/drivers/model warmup, private storage/identity, ingress TLS/WebSockets/Streamlit affinity, resource budgets, bounded pools and independent worker/model scaling. CI/CD/Terraform/Helm manage placement/resources; same application interfaces remain. Use schema expand/contract and isolated model/index versions for safe promotion/rollback. Verify actual GPU use, auth/quality parity, migration and restore before launch. Local/fake tests are not GPU/HA evidence.

Keep 1,000–5,000 RPS as an unverified design objective. Define route mix, prompt/output lengths, corpus/session/upload sizes, latency/error budgets, hosting and GPU budget before sizing; none blocks local coding. Benchmark metadata, fresh chat, ingestion, mixed and actual browser/WebSocket profiles separately. Measure offered/admitted/completed work, queue age/growth, token rates, p95/p99 latency, polling overhead, memory and storage costs. A `202` or `429` is not a completed answer; mocks/cache hits must be labeled separately.

Sizing: mean in-flight = completed requests/second × mean latency; output token demand = fresh answers/second × mean output length. At 5,000 fresh answers/second and 400 output tokens each, output demand is 2 million tokens/second. At 5,000 new jobs/second, 24-hour retention is 432 million jobs, excluding retries/indexes/receipts/WAL/backups. Size metadata/object payloads and prove cleanup keeps pace using pre-aged data, not a short soak alone.

Later representative tests progress through 1,000/2,500/5,000 offered RPS with predeclared SLOs, sustained/soak/burst runs and model/worker/broker/database/storage failure tests. Report hardware/config/model identity and actual results. Validate supported Chroma topology rather than sharing a standalone volume across replicas. Instrument sanitized request/job traces, rates, latency, query embedding wait, queues, GPU/storage/pool saturation and backup/journal health. No broad application rewrite is intended, but a measured component bottleneck can require a reviewed targeted change.

Official references for setup verification: [Ollama CPU/GPU](https://docs.ollama.com/docker), [Streamlit identity](https://docs.streamlit.io/develop/concepts/connections/authentication), [Streamlit replicas](https://docs.streamlit.io/develop/concepts/architecture/architecture), [Chroma architecture](https://docs.trychroma.com/reference/architecture/distributed), [Celery tasks](https://docs.celeryq.dev/en/stable/userguide/tasks.html). Verify exact pinned versions during implementation.
