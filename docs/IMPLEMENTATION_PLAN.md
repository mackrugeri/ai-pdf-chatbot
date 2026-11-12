# Implementation Plan: AI PDF Chatbot

Status: planned production work; no implementation milestone completed by this document
Version: 2.1
Date: 2026-11-13

## 1. Delivery approach

Implement [PRD.md](PRD.md) using [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md), [TECH_STACK.md](TECH_STACK.md), and [CAPACITY_PLAN.md](CAPACITY_PLAN.md). Keep the main stack and PostgreSQL. The user-confirmed objective is 1,000–5,000 RPS. A local demo, an architecture diagram, or an acceptance-only benchmark cannot certify it.

The previous 15-day learning schedule is superseded. Deliver in dependency-ordered phases and estimate dates after resolving workload/infrastructure choices. Hosting purchases and deployment are separate actions; this plan does not authorize spending or create infrastructure. Work in `/Users/Ahsan/Documents/Projects/ai-pdf-chatbot`.

## 2. Phase 0: Requirements, component feasibility, and sizing inputs

- [ ] Define endpoint mix, including 100% fresh-chat demand, prompt/output distributions, corpus size, upload byte rate, active sessions, and user quotas.
- [ ] Agree p95/p99 API/complete-answer latency, acceptance/error budgets, queue deadlines, availability, retention, and RPO/RTO targets.
- [ ] Select hosting/region and budget; benchmark candidate GPU/model configuration before estimating replica counts.
- [ ] Verify Streamlit authentication/token integration, WebSocket affinity, upload buffering, session behavior, and representative session capacity.
- [ ] Verify the deployable Chroma topology, licensing, isolation filters, throughput, and recovery model.
- [ ] Validate RabbitMQ/Celery delivery behavior and model-serving admission under intended versions.
- [ ] Define hot-row/index/payload sizes, peak new-job rate, retention windows, partition/lookup/idempotency constraints, cleanup throughput, and storage/WAL/backup budgets.
- [ ] Select/test immutable object acceptance and an independently protected deletion journal with replay/cutover guarantees.
- [ ] Record dependency/model licenses and tested compatibility; approve any needed stack changes explicitly.

Exit: workload and SLO file is concrete, capacity risks are recorded, and no known main-stack blocker is hidden. Covers NFR-03 and NFR-06. Do not build a large deployment before these feasibility checks.

## 3. Phase 1: Reproducible foundation and identity

- [ ] Create Python configuration, uv lockfile, dependency groups, application modules, Ruff/pytest settings, safe `.env.example`, `.gitignore`, and README.
- [ ] Add API versioning, schemas, sanitized errors/request IDs, liveness/readiness, and dependency injection.
- [ ] Create immutable API/UI/worker Docker images and small-scale Compose integration services.
- [ ] Implement OIDC login, supported API access-token flow, independent JWT validation/key rotation, internal user mapping, and logout/expiry behavior.
- [ ] Add PostgreSQL schemas/versioned migrations, bounded connections, and dedicated test database.
- [ ] Add private object-store adapter, secret references, and a sanitized logging/metrics baseline.

Exit: authenticated API/UI skeleton, isolated tests, and reproducible local integration. Missing/forged/wrong-audience tokens fail; secrets/content do not leak. Covers FR-05, NFR-02, and NFR-05.

## 4. Phase 2: Authorized uploads and PDF processing

- [ ] Implement owner-scoped document state, upload reservations, verified version-pinned staging, server-only immutable final promotion, checksums, and idempotent duplicate/completion handling.
- [ ] Test staging URL reuse, overwrite during/after completion, pinned-version downloads, and crash recovery around promotion.
- [ ] Enforce byte/page/text/token limits and per-owner storage quotas across concurrent requests.
- [ ] Parse in resource-limited, network-disabled workers/subprocesses; reject malformed/encrypted/textless PDFs and report mixed-page limitations.
- [ ] Create deterministic page-aware chunks and version/index fingerprints.
- [ ] Test blank-page numbering, Unicode, long pages, malicious filenames, malformed files, over-limit inputs, owner-scoped duplicates, and abandoned-object cleanup.

Exit: valid uploads are traceable and isolated; invalid inputs fail without exhausting API resources. Covers FR-01, FR-03, FR-05, FR-07, and FR-12.

## 5. Phase 3: Durable execution and persistent indexing

- [ ] Implement jobs/idempotency, transactional outbox, publisher confirms, and broker reconciliation.
- [ ] Configure separate ingestion/answer/cleanup queues with bounded concurrency/prefetch and tested late acknowledgments.
- [ ] Add attempt leases, heartbeats, publication fencing, deadlines, cancellation, bounded retries, and failed-job inspection.
- [ ] Implement Ollama embedding adapter, pinned model identity, bounded batching, no silent truncation, and service readiness.
- [ ] Persist versioned Chroma records through a service adapter; publish ready versions only after complete verified indexing.
- [ ] Test duplicate delivery, outbox-publish crashes, broker outage, worker death, partial vectors, stale attempts, and reindex compatibility.

Exit: accepted ingestion survives restarts without duplicate visible data or lost authoritative state. Covers FR-02, FR-04, FR-10, and NFR-04.

## 6. Phase 4: Private retrieval, inference, and answers

- [ ] Implement owner/selected-version filtered retrieval and metadata verification.
- [ ] Build dedicated embedding/generation endpoint routing with distributed capacity budgets, fair per-owner admission, queue deadlines, and safe timeout handling.
- [ ] Implement full-prompt token budgets, untrusted-source delimiters, structured response validation, source mapping, and bounded repair.
- [ ] Store short-lived encrypted payload/result objects with compact PostgreSQL control rows; reauthorize documents/results at publication and read time.
- [ ] Implement owner-scoped `GET /api/v1/jobs` with bounded keyset pagination/filtering and no content payloads; test cursor ownership, equal timestamps, concurrent arrivals, expiry, and empty-session rediscovery.
- [ ] Add partitioned history/retention jobs, independent idempotency receipts, orphan cleanup, and byte/cleanup-lag metrics; test expiry cannot resubmit duplicate work or drop running jobs.
- [ ] Test missing evidence, invented markers, malformed model output, token overflow, timeouts with unknown execution, expired jobs, and cross-owner result/cache isolation.
- [ ] Create a tuning set separate from the frozen 100-case release evaluation.

Exit: supported answers have checkable authorized citations; no-evidence questions abstain; saturated inference fails predictably. Covers FR-05 through FR-08, FR-10, and FR-11.

## 7. Phase 5: Deletion, retries, retention, and UI

- [ ] Implement journal-first deletion with durable independently protected intents before database tombstones/outbox cleanup; handle journal outage, partial transaction failure, retries, and intent reconciliation.
- [ ] Add cancellation, cache/result invalidation, and idempotent file/vector cleanup for tombstoned documents.
- [ ] Prevent stale workers from publishing deleted documents or answers; expose deletion completion status.
- [ ] Apply retention for results, abandoned uploads, audit/logs, tombstones, and backups; document signed-URL and already-sent-response boundaries.
- [ ] Build Streamlit sign-in, upload/progress, selection, chat job status, source display, retry/cancel/delete controls, and safe logout.
- [ ] Add jittered/backoff/conditional polling, session affinity, safe rendering, and reconnect restoration using job discovery without browser-held IDs.
- [ ] Test deletion during generation/retry, UI replica loss, upload retries, access revocation, and session/cache separation.

Exit: full authorized flow works across replicas, deletion excludes content immediately, and user state survives expected reconnects. Covers FR-08, FR-09, and FR-12.

## 8. Phase 6: Operational infrastructure and secure release pipeline

- [ ] Add Kubernetes/Helm manifests for separate API/UI/worker/router/GPU pools, resource budgets, health probes, drains, network policies, secrets, and disruption policies.
- [ ] Configure ingress TLS, WebSocket affinity, body limits, distributed rate/admission limits, and connection budgets.
- [ ] Implement/test PostgreSQL HA/PITR, broker quorum recovery, Redis failure behavior, object backups, and supported Chroma backup/restore.
- [ ] Keep the deletion journal outside the application restore boundary with restricted append-only retention; implement closed-access restore, current-ledger replay, coverage checks, writer fencing, and cutover checkpoints.
- [ ] Add OpenTelemetry correlation, Prometheus metrics, Grafana dashboards, queue/deletion/backup alerts, and incident runbooks.
- [ ] Add CI for lint/tests, storage integration, dependency/image/secret scans, immutable build, staging migrations, canary, and rollback checks.
- [ ] Exercise schema expand/contract and previous-image rollback; do not rely on destructive down migrations for recovery.

Exit: staging is reproducible and operable; failover, restore, rollback, and alert drills have evidence and an assigned operational owner. Covers FR-13 and NFR-02/NFR-05/NFR-07/NFR-08.

## 9. Phase 7: Quality and capacity certification

- [ ] Freeze/version at least 100 release cases: 80 answerable and 20 unsupported, with expected evidence and adversarial/selection cases.
- [ ] Meet PRD targets: at least 90% supported-answer success, at least 95% unsupported abstention, all citation references valid, and zero isolation/deletion failures.
- [ ] Benchmark components with realistic datasets and model lengths; estimate hardware and safe replica counts from actual measurements.
- [ ] Execute separate metadata, fresh-chat, ingestion, mixed, and browser profiles at 1,000, 2,500, and 5,000 offered RPS as applicable.
- [ ] Measure accepted versus completed work, p95/p99 latency, token rates, queue growth, retries, polling traffic, and resource/cost metrics.
- [ ] Run 30-minute sustained stages, a two-hour target-profile soak, overload/burst tests, and node/broker/database/model failures.
- [ ] Sustain admitted-job retention/expiry under target volume; measure rows/indexes, payload bytes, WAL/replicas, backups, partition rotation, orphan cleanup, idempotency storage, and oldest cleanup age against agreed budgets.
- [ ] Verify load generators are not saturated; reject profiles with hidden dropped arrivals or unbounded queues.
- [ ] Publish results and blockers; do not claim 5,000 fresh answers/second based on submissions or cheap API reads.

Exit: agreed workload and SLOs pass, or a narrower achieved profile is explicitly reported and approved. No component gets bypassed to manufacture a pass. Covers NFR-03 and the PRD release gates.

## 10. Phase 8: Release handoff

- [ ] Document exact setup/deployment, model/index identities, API contracts, quotas, retention, limitations, cost envelope, and certified capacity profile.
- [ ] Acknowledge a deletion after a backup, restore that older backup, and prove current independent journal replay prevents resurrection before access/dispatch resumes; journal gaps must keep readiness closed.
- [ ] Verify journal coverage and cutover during concurrent deletion attempts; meet measured RPO/RTO or record a blocking failure.
- [ ] Verify monitoring ownership, certificate/credential rotation, incident response, dependency/model update policy, and deletion support process.
- [ ] Run clean deployment, representative user acceptance, canary promotion, and rollback rehearsal.
- [ ] Record release evidence and known limitations; obtain release approval for a specific environment.

Exit: production readiness is demonstrated, not inferred from documentation or framework choices.

## 11. Commit and verification strategy

Keep meaningful implementation changes and their tests together: foundation/auth, metadata/migrations, uploads, durable jobs, indexing, private retrieval, inference/results, deletion, UI, infrastructure, and capacity evidence. Do not create empty modules to mirror a plan. Test units with fakes; integration-test actual isolated PostgreSQL/broker/object/vector services; evaluate actual models and actual UI separately. Re-run affected checks after changes and re-certify performance when model, tokenizer, chunking, topology, or workload changes.
