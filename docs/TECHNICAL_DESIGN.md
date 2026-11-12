# Technical Design Document: AI PDF Chatbot

Status: production architecture baseline; not implemented or load-certified
Version: 2.0
Date: 2026-11-13

Requirements: [PRD.md](PRD.md). Choices: [TECH_STACK.md](TECH_STACK.md). Sizing: [CAPACITY_PLAN.md](CAPACITY_PLAN.md). Delivery: [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).

## 1. Architecture and boundaries

Main stack: **Python, Ollama, Qwen3 4B, LlamaIndex, ChromaDB, FastAPI, Streamlit**. PostgreSQL owns application metadata. Target traffic is 1,000–5,000 RPS; exact endpoint mix and inference SLOs are unresolved. This architecture provides scale boundaries, not a claim that a particular deployment sustains the target.

```text
Browser -> TLS ingress / rate limits
                |
                +-> Streamlit replicas (WebSockets + session affinity)
                |        -> authenticated server-to-server API calls
                +-> FastAPI replicas (stateless authenticated API)
                           |
                           +-> PostgreSQL + connection pooler
                           |     ownership, documents, jobs/results, outbox
                           +-> Redis (quotas, admission, bounded caches)
                           +-> private object storage (PDFs/artifacts)
                           +-> transactional outbox -> RabbitMQ
                                                        |
                   +------------------------------------+
                   v                  v                  v
             ingestion workers   answer workers    cleanup workers
                   |                  |
             sandboxed PDF       authorized retrieval -> Chroma service
             parse/chunk              -> inference router -> Ollama GPU pool
                   |                                            (Qwen3 4B)
                   +-> embedding router -> Ollama embedding pool
                   +-> versioned Chroma records

All services -> sanitized metrics/logs/traces -> operational monitoring
```

API/UI processes do not run ingestion or model generation. Queue messages carry job IDs, not PDF text or tokens. Workers read job ownership and payload from PostgreSQL. UI never accesses application databases or inference endpoints directly. Durable authoritative files live in object storage, not replica-local paths. Chroma runs as a separately operated service with a validated deployment topology, not an embedded index copied into each API pod.

## 2. Authentication and authorization

Integrate an OIDC provider capable of issuing access tokens for the FastAPI audience. Streamlit authenticates the user and obtains that access token server-side through a supported tested flow. FastAPI independently validates signature, allowed algorithm, issuer, audience, expiry, and required scopes using bounded/cached JWKS retrieval and key rotation handling. An ID token or an unsigned owner header is not an API credential. Select and verify the actual provider/refresh/logout behavior before release; auth integration is a blocking milestone.

Map `(issuer, subject)` to an internal user UUID. Derive `owner_id` from the validated identity, never from client data. All repository queries for documents, jobs, sources, retries, uploads, and downloads include owner constraints. Return a uniform `404` for nonexistent and inaccessible resource IDs. Administrative operations require separate scopes and do not grant routine access to document content.

Attach owner and document/version IDs to Chroma records. Apply owner + selected-ready-document filters before retrieval and verify returned metadata against the authorized set. Cache keys include owner, document versions, index fingerprint, and normalized query/configuration. Recheck current authorization and deletion state before serving any cached/result payload. Avoid globally shared per-user Streamlit caches. Keep secrets/tokens out of logs, URLs, rendered content, and durable job payloads.

## 3. PostgreSQL and object storage

Use PostgreSQL with Psycopg 3, bounded pools, and a measured PgBouncer connection budget across all replicas and workers. Use parameterized SQL and short transactions. Never hold database locks/connections across parsing, vector calls, or inference. Apply explicit versioned SQL migrations via a controlled release job, with backward-compatible expand/contract changes. Use a separate test database and least-privilege application/migration/backup roles.

Proposed tables:

- `users`: internal ID, issuer, subject, active state; unique `(issuer, subject)`.
- `documents`: ID, owner ID, original filename, private object key, SHA-256, page/textless-page/chunk counts, status, active version, index fingerprint, error code, timestamps; unique `(owner_id, sha256)` for live documents.
- `document_versions`: immutable version/index identity, expected chunk count, artifact references, publication state.
- `jobs`: ID, owner ID, type, document/version references, bounded payload, state, idempotency key/hash, deadline, attempt count, lease token/expiry, heartbeat, result/error reference, timestamps.
- `outbox`: event ID, job ID, publication state, retry timestamps; committed with job creation.
- `audit_events` and `deletion_tombstones`: minimal actor/action/resource/time metadata, without excerpts or questions.

Index owner/time listing, job state/deadline, outbox publication, and ownership/reference lookups. Use keyset pagination; avoid unbounded result lists. Benchmark job/result write amplification and retention cleanup.

Object keys use generated owner/document/version IDs; user filenames are display-only. Keep a private staging prefix, final PDF objects, and optional extracted-text artifacts. Enforce encryption at rest, private access, bounded short-lived signed URLs, checksums, and lifecycle cleanup of abandoned uploads. Signed URLs are not revocable after issuance: set short TTLs and authorize issuance; no object key is a substitute for ownership checks.

## 4. Upload and ingestion protocol

1. Authenticated client initiates an upload with size/name metadata and idempotency key. API reserves quota and creates a pending owner-scoped document/upload record.
2. Return a bounded upload target. The Streamlit server streams bytes to private object storage without retaining the full file in its own long-lived state. Prototype direct-to-object browser uploads only if compatible with the selected Streamlit flow; do not assume this exists automatically.
3. Complete-upload verifies stored size/checksum and schedules a durable job in the same PostgreSQL transaction as an outbox event. Byte-identical owner duplicates return the existing document; delete abandoned objects and release reservations.
4. Outbox publishers send persistent job IDs with broker publisher confirms and then mark published. A crash between publish and marking can duplicate delivery; workers must be idempotent.
5. Ingestion workers claim job attempts with database leases. Parse PDFs in restricted subprocesses/containers with CPU, memory, time, file-size, and network limits. Validate actual PDF content, encryption, page count, total extracted text, and supported scope.
6. Extract page-level text, preserving original 1-based PDF indices including blank-page gaps. Make deterministic page-bounded overlapping chunks with guaranteed progress.
7. Embed bounded batches using the pinned embedding identity and dedicated embedding capacity. Disable silent truncation; fail clearly for unsupported input size.
8. Upsert deterministic versioned chunk IDs to Chroma. Verify expected records, then atomically publish the ready version in PostgreSQL, guarded by attempt lease/version and document not-deleting state.
9. Failure/retry never exposes partial indexes. Reconciler cleans orphan versions/objects and detects stalled jobs. Retry transient failures with capped exponential backoff/jitter; invalid files fail permanently with useful messages.

Initial limits retained for testing: 20 MiB/file, 300 pages/file, 2 million extracted characters, 2,000 question characters, and 10 selected documents. They are service defaults, not a capacity promise. Tenant storage/upload/job quotas and global queue budgets must be selected from the capacity model before release.

## 5. Durable jobs and inference scheduling

Use Celery with RabbitMQ durable quorum queues, publisher confirms, persistent messages, tested late acknowledgments, bounded prefetch, and capped retries. Separate ingestion, answer, and cleanup queues so a large PDF workload does not starve answers or deletion. Validate broker/client behavior for chosen versions. JSON-only messages; never accept arbitrary serialized tasks from untrusted networks.

PostgreSQL is authoritative for acceptance, progress, and results. Broker delivery is at least once, not exactly once. Workers use atomic lease/attempt tokens; duplicate or stale attempts cannot publish results or ready indexes. Heartbeat and cancellation checks occur between expensive steps. If an inference request times out with execution state unknown, quarantine its capacity slot until the old request is confirmed finished or its endpoint is reset; do not blindly retry and double-load the GPU.

Reconcile jobs against outbox/broker/leases to recover missed or duplicate delivery. Cancellation and expiration are durable state changes. Deletion marks related jobs cancelling and prevents their publication. Completed answers may be retried internally, but only one current authorized result is published for a job. Idempotency keys are owner+endpoint scoped with request hashes; reusing a key with a different body returns conflict. Keep idempotency metadata at least as long as the documented client retry horizon.

Inference routers track healthy warmed endpoint inventories and per-instance concurrency/memory budgets. Keep embedding and generation pools separate. Distributed admission counters/leases enforce measured capacity across answer workers; local semaphores alone are insufficient. Redis loss fails new admission closed or returns `503`, while PostgreSQL preserves accepted jobs. Queues have maximum depth/age and per-user fair-share limits. Return `429` with `Retry-After` or `503` when budgets are exhausted; no unbounded waiting and no performance claim based on rejection-only throughput.

## 6. Retrieval and grounded answers

Answer worker resolves current owner access and document ready versions before retrieval. Empty selection never means all documents. Embed the question, retrieve up to six filtered candidates initially, and revalidate source ownership/version. Assemble delimited untrusted excerpts labeled `S1`, `S2`, etc. Start with page chunks of roughly 1,200 characters with 200 overlap and a 4,000-character context cap; measure/tune with versioned indexes.

Use the pinned model tokenizer or a tested conservative full-prompt token budget check; character caps alone do not bound tokens. Initial requested model context is 8,192 tokens with at most 1,024 output tokens, subject to model validation and workload sizing. Reduce excerpts to leave output headroom, and reject questions that cannot fit. Typical and worst-case lengths must appear separately in load tests.

Prompt instructs evidence-only answers, abstention, citation markers, and ignoring document instructions. No action tools are exposed. Validate structured `answer`, `source_ids`, and `insufficient_evidence` output. Every supported result needs valid inline source markers; resolve filename/page/excerpt server-side from supplied sources. Allow one bounded format-repair attempt, then fail clearly. No retrieved evidence yields deterministic abstention without generation. Identifier checks cannot establish semantic grounding; evaluate with human-labeled cases.

Before publishing and before serving results, recheck user/document status. Deleted/revoked sources invalidate the answer; do not merely remove citations while preserving potentially sensitive answer text. Log no raw question, excerpt, answer, or model reasoning by default. Session history does not influence retrieval in this release; recent request results are persisted only for reconnect/retry.

## 7. Deletion, retention, and consistency

DELETE transaction tombstones the owner-scoped document, invalidates versions, cancels related jobs, records an outbox cleanup job, and returns `202`. New list/retrieval/download/result reads exclude it immediately. A bounded in-flight response that crossed the final authorization check before deletion may finish; deletion cannot retract bytes already sent or previously issued signed URLs. Document this boundary explicitly.

Cleanup workers remove PDF/artifact objects, vector versions, affected saved answers/excerpts, and cache entries; retries and deletion status remain visible. Stale ingestion/answer workers cannot republish deleted data because publication is guarded by current database state and attempt/version tokens. Keep minimal tombstones until all live stores, replicas, caches, and applicable backup retention windows are covered.

Proposed defaults: request/result payloads 24 hours, abandoned uploads 1 hour, sanitized operational logs/audit events 30 days, encrypted backups 30 days; retained document originals persist until user deletion. Finalize these before release. Backups are not instantly erased on a delete: disclose expiry policy, restrict access, and reapply tombstones before any restored environment is served. Document metadata can be minimized after cleanup while retaining the deletion ledger needed to prevent resurrection.

## 8. Versioned API

Protected prefix: `/api/v1`. Bearer access token on every data route. Common error: `{error:{code,message,retryable},request_id}`; no internal paths, SQL, tokens, or stack traces. Enforce body limits, request deadlines, pagination, idempotency, and distributed quotas before expensive work.

| Method / path | Contract |
| --- | --- |
| `GET /health/live` | Minimal unauthenticated process liveness; no dependency details. |
| `GET /health/ready` | Internal/operator readiness; app DB/schema and required connections, not an expensive model call per probe. |
| `GET /api/v1/capabilities` | Authenticated sanitized ingestion/answer availability and limits. |
| `POST /api/v1/uploads` | `{filename,size_bytes}` + idempotency key -> `201` upload/document ID and expiring upload target. |
| `POST /api/v1/uploads/{id}/complete` | Verify object + enqueue -> `202` job/document refs; owner duplicate may return `200` existing refs. |
| `GET /api/v1/documents` | Cursor-paginated owner document summaries. |
| `GET /api/v1/documents/{id}` | Owner document status, counts, and sanitized failure details. |
| `GET /api/v1/documents/{id}/download` | Authorized short-lived download target, if enabled. |
| `POST /api/v1/documents/{id}/retry` | Retry eligible failed ingestion -> `202`; requires intact original and compatible configuration. |
| `DELETE /api/v1/documents/{id}` | Tombstone + cleanup -> `202` deletion job; repeated delete returns existing deletion status. |
| `POST /api/v1/chat` | `{question,document_ids}` + idempotency key -> `202` answer job, not a completed answer. |
| `GET /api/v1/jobs/{id}` | Owner-scoped state/progress, polling hint, expiry, and result when complete. Supports ETag/conditional reads. |
| `POST /api/v1/jobs/{id}/cancel` | Idempotent cancellation request; running operations stop at safe checkpoints. |

Chat result: `{answer,insufficient_evidence,sources:[{source_id,chunk_id,document_id,document_version,filename,page_number,excerpt}]}`. Jobs: queued/running/retrying/succeeded/failed/cancelling/cancelled/expired. Documents: uploading/queued/processing/ready/failed/deleting/deleted. Deleted tombstone access exposes only sanitized owner deletion status, not old content.

HTTP mappings: `401` invalid/missing token; `403` missing operation scope; `404` absent/inaccessible object; `409` invalid state, index mismatch, or idempotency conflict; `410` expired owner job result; `413` oversized request/file; `415` unsupported PDF type; `422` schema/content validation; `429` quota/admission limit; `503` dependency/capacity unavailable. Worker/model timeouts and invalid responses are stored as sanitized job errors because the earlier submission already returned `202`.

## 9. UI and caching at scale

Streamlit retains UI responsibility. Load balancer must support WebSockets, sticky sessions, trusted forwarded headers, consistent cookie secrets, and appropriate timeouts. Replica termination drains connections; reconnect restores recent request status from the API rather than assuming session state is durable. Replicas share no user data through global caches. Built-in upload buffering and rerun costs must be profiled, even if object storage is the durable destination.

Poll only active jobs with server hints, exponential backoff, jitter, and conditional reads; never poll all documents from all idle sessions every two seconds. Count polling and auth traffic in total offered load. On logout/token expiry, discard user session data and stop protected calls until reauthentication. Render model/PDF content safely without unsafe HTML. Client errors must not cause automatic duplicate job submission.

## 10. Deployment, telemetry, and recovery

Use immutable Docker images and Kubernetes manifests/Helm for independently scaled API, UI, ingestion, answer, cleanup, and model-router workloads. GPU pools preload pinned Ollama models; Mac development can use native Ollama. Autoscale API on latency/inflight/CPU, workers on queue age/depth and effective service rate, GPU replicas on safe token capacity/utilization and warmup time; reserve capacity for scale-up delays. Set resource requests/limits, bounded pools, readiness/startup/liveness probes, graceful drain, disruption policies, and private network policies.

PostgreSQL needs tested standby/failover, backups/PITR, and connection limits. Broker quorum queues need appropriate failure-domain placement. Redis HA/failover and loss semantics must be tested. Object storage and Chroma need a supported redundancy/restore plan. Do not run multiple standalone Chroma replicas against a shared persistent directory. Confirm distributed Chroma's selected offering/deployment availability, licensing, and operational requirements before production signoff.

Use OpenTelemetry request/job correlation and sanitized logs, Prometheus metrics, and Grafana dashboards. Track offered/admitted/completed RPS by endpoint, p50/p95/p99 latency, queue age, retries, outstanding jobs, token rates, GPU memory, DB pools/replication lag, vector latency, upload throughput, deletion backlog, and backup freshness. Alert on SLO burn, stalled queues, model failures, pool saturation, and lost backup/replication health. Do not use user/document IDs as high-cardinality metric labels.

Release through CI checks -> immutable images/scans -> isolated staging -> migration compatibility -> real-model evaluations -> capacity/fault tests -> canary -> monitored promotion or rollback. Restore drills cover PostgreSQL, objects, deletion ledger, model/index identity, and Chroma snapshots/rebuilds. Rebuild duration must fit RTO; otherwise maintain a tested restorable vector snapshot. [CAPACITY_PLAN.md](CAPACITY_PLAN.md) defines proof required before any 5,000-RPS claim.

## 11. Verification and unresolved decisions

Automate owner isolation, version filtering, pagination/idempotency, duplicate delivery, lease fencing, worker death, object/vector partial failure, deleting-during-generation, token expiry/key rotation, and migration compatibility tests. Use temporary object/vector namespaces and separate real service databases. Run browser/WebSocket tests for Streamlit; API-only tests do not prove the UI path.

Before release resolve workload mix/SLOs, corpus/session sizes, hosting/GPU budget, identity provider, object-storage provider, exact Chroma topology, retention, and measured autoscaling thresholds. Preserve main-stack choices unless the owner approves a change after evidence. This document supersedes the in-process queue, process-local locks, local-only uploads, and single-worker architecture from version 1.

Official design references: [Streamlit auth](https://docs.streamlit.io/develop/concepts/connections/authentication), [Streamlit replication](https://docs.streamlit.io/develop/concepts/architecture/architecture), [Chroma distributed architecture](https://docs.trychroma.com/reference/architecture/distributed), [Celery task semantics](https://docs.celeryq.dev/en/stable/userguide/tasks.html), [PostgreSQL backup methods](https://www.postgresql.org/docs/current/backup.html), and [Kubernetes autoscaling](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/). These inform the proposal; compatibility/capacity still need implementation verification.
