# Implementation Plan: Local Portfolio to GPU Deployment

Status: planned work; no implementation milestone completed by this document
Version: 3.0
Date: 2026-11-13

## 1. Scope and milestones

Build the production-oriented architecture locally without a dedicated GPU. Preserve Python, Ollama, Qwen3 4B, LlamaIndex, ChromaDB, FastAPI, Streamlit and PostgreSQL. No GPU hardware, production cluster, provider purchase, or 5,000-RPS benchmark is required to start development or complete the portfolio engineering milestone.

Follow [PRD.md](PRD.md), [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md), [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md), and [DECISION_LOG.md](DECISION_LOG.md). The former 15-day roadmap is superseded; estimate work after the local foundation spike. Contracts remain the same across environments; settings, service placement and replica/resource budgets change.

- **A: local portfolio implementation:** working local application, real storage/job/auth boundaries, automated tests, honest model evidence, and permitted-data demo.
- **B: deployment preparation:** immutable images, local integration setup, GPU/Kubernetes manifests, configuration map, and runbooks authored/validated without provisioning hardware. Real GPU checks remain explicitly pending.
- **C: production verification:** future representative infrastructure, semantic/capacity/fault/HA/restore checks and environment-specific release decision. Not a prerequisite for A or authoring B.

Nothing here authorizes infrastructure spending or a production launch. Planning/checklists do not establish that code, tests, manifests or benchmarks already exist.

## 2. Phase 0: Local feasibility and contracts (A)

- [ ] Record confirmed choices, local constraints, proposed supporting services and future production decisions in the decision log.
- [ ] Verify supported Python/dependency compatibility and licensing; create a small resource inventory without assuming a dedicated GPU.
- [ ] Spike Ollama adapter protocol with deterministic fakes first; optionally test real CPU/native Qwen3/Nomic if resources permit.
- [ ] Select a local OIDC provider and a local S3-compatible service that pass the needed auth/versioning/checksum/policy contracts.
- [ ] Define small local fixtures, one-model-operation scheduling, low local workload limits and mode labeling.
- [ ] Write storage/job/model interfaces and configuration contracts before domain logic; keep auth/ownership enabled in local integration.

Exit: local implementation can begin with no cloud/GPU prerequisites. Future GPU benchmarks, provider selection and production SLO/budget decisions are tracked, not treated as blockers to A.

## 3. Phase 1: Foundation, identity and services (A)

- [ ] Create Python project, uv lockfile, modules, Ruff/pytest, typed settings, safe `.env.example`, `.gitignore`, and verified README commands.
- [ ] Add API versioning, errors/request IDs, schemas, readiness/liveness and dependency injection.
- [ ] Implement deterministic and Ollama model adapters behind the same ports; production rejects fake/test configurations.
- [ ] Add incrementally runnable Compose profiles and API/UI/worker images; no CUDA/GPU requirement in the default local profile.
- [ ] Implement local OIDC login/access-token integration, independent API token validation, user/owner mapping, expiry/logout/deactivation tests.
- [ ] Add PostgreSQL schema/versioned SQL migrations, bounded pools, isolated test database and object-store adapter.
- [ ] Add baseline sanitized metrics/logging; keep full monitoring optional locally.

Exit: reproducible authenticated local skeleton; malformed/wrong-audience credentials and cross-user access fail; no secret/content leakage. Covers FR-05, NFR-02/NFR-05/NFR-10.

## 4. Phase 2: Immutable uploads and PDF extraction (A)

- [ ] Implement owner-scoped uploads, quota reservation/release, verified version-pinned staging and server-only immutable final promotion.
- [ ] Add duplicate/completion idempotency and crash/orphan cleanup; test overwrite during/after completion and pinned downloads.
- [ ] Parse in resource-limited network-disabled subprocesses; reject invalid/encrypted/textless/over-limit PDFs and report mixed-page gaps.
- [ ] Create deterministic page-bounded chunks preserving PDF page indices and source ownership.
- [ ] Test Unicode/blank/long pages, malicious filenames, size limits, duplicate owners, abandoned uploads and wrong-owner IDs.

Exit: accepted immutable bytes are traceable and private, with bounded resource use. Covers FR-01/FR-03/FR-07/FR-12.

## 5. Phase 3: Durable jobs and attempt-safe indexing (A)

- [ ] Implement PostgreSQL jobs/idempotency receipts/outbox and real RabbitMQ integration with confirmed publication.
- [ ] Separate ingestion/answer/cleanup workers and add leases, heartbeat, fencing, deadlines, cancellation, retries and reconciliation.
- [ ] Store bounded control rows and object payload references; retain active inputs through recovery grace.
- [ ] Implement real/fake embeddings in separate model/index namespaces; verify dimensions, identity and no silent truncation.
- [ ] Write Chroma records/artifacts into new attempt-specific namespaces; atomically publish only the winning verified attempt pointer.
- [ ] Restrict stale-attempt cleanup to its own namespace; test a paused loser resuming writes/cleanup after its retry has published.
- [ ] Test broker/API/worker crashes, duplicate delivery, partial vectors, lease expiry and schema/index compatibility.

Exit: accepted local jobs survive restart, partial/loser indexes stay invisible, and stale workers cannot mutate/delete winning data. Covers FR-02/FR-04, NFR-04.

## 6. Phase 4: Authorized retrieval and answers (A)

- [ ] Filter by owner, selected ready version and published attempt before retrieval; verify all returned metadata.
- [ ] Implement query versus ingestion embedding queues with a guaranteed query share and bounded fairness. Locally serialize shared model work; production can map the same classes to reserved endpoint pools.
- [ ] Build full-prompt budgets, untrusted-source delimiters, structured answers/citation validation, abstention and bounded repair.
- [ ] Persist short-lived encrypted result payloads; authorize at publication/read and invalidate whole answers referencing deleted sources.
- [ ] Implement paginated owner-scoped job discovery/detail with cursor integrity, expiry and complete-session-loss tests.
- [ ] Add terminal-history retention/partition strategy and independent receipt retention; never drop active jobs/inputs or convert expired retries into new work.
- [ ] Keep input/result TTL, quotas, schema/index/WAL costs and cleanup metrics measured at local scale; future capacity sizing remains separate.

Exit: safe orchestration works with fakes; opt-in real-model runs provide separately recorded semantic evidence. Covers FR-05 through FR-08/FR-10/FR-11 and NFR-09/NFR-10.

## 7. Phase 5: Deletion, UI and local recovery (A)

- [ ] Implement journal-first deletion with independently modeled local namespace/credentials, database tombstones/outbox and partial-failure reconciliation.
- [ ] Prevent stale publication; delete applicable object versions, result payloads, multipart remnants, attempt vectors and caches through retryable cleanup.
- [ ] Implement closed-access restore and journal replay/checkpoints; test a backup older than acknowledged deletion and missing-journal failure.
- [ ] Build Streamlit sign-in/upload/status/selection/chat/source/retry/cancel/delete views with safe rendering, mode labels and bounded polling.
- [ ] Restore recent jobs from the API after empty-session reconnect; verify token expiry/deactivation/logout and user cache isolation.
- [ ] Exercise ingestion flood versus query scheduling, deletion-during-generation, local replica loss, retention and idempotency expiry.

Exit: reproducible full local workflow and fault checks pass. A local journal on the same disk simulates the independent contract; laptop-loss durability is not claimed. Covers FR-08/FR-09/FR-12/FR-13.

## 8. Phase 6: Portfolio handoff and deployment artifacts (A + B)

- [ ] Record actual local test results, permitted-data demo, architecture diagrams, model/configuration identity, limitations and evidence labels.
- [ ] Create a tuning set plus frozen 100-case semantic release set; only actual-model runs count toward the PRD quality target. Record not-run tests honestly.
- [ ] Document verified startup/test/reset/backup commands, estimated local footprint and host/container troubleshooting; do not publish nonexistent setup instructions.
- [ ] Build target-platform images and author/render Helm/Kubernetes templates, resource settings, GPU/runtime/model warmup, ingress affinity/TLS and private network/secrets rules.
- [ ] Add CI lint/tests/integration/image checks and staging/migration/canary/rollback workflow definitions; run only resource-available stages, with pending external stages visible.
- [ ] Author dashboards/runbooks and migration/restore/retention procedures; rehearse feasible single-machine cases.
- [ ] Publish a portfolio evidence report distinguishing implemented/tested, authored/unverified and future production-only work.

Exit A: local engineering deliverable works and is reproducible. Exit B: deployment artifacts and contracts are prepared with unverified GPU/HA/capacity work explicitly listed. Neither permits an achieved 5,000-RPS claim.

## 9. Phase 7: Future GPU staging (C, when resources exist)

- [ ] Finalize workload, token lengths, corpus/session/upload sizes, SLOs, provider/region, identity, Chroma topology, retention, budget and operational ownership.
- [ ] Provision isolated resources only when authorized; verify GPU drivers/runtime, native dependency/platform compatibility and actual model device use.
- [ ] Configure private real Ollama endpoint inventory, warmup, safe concurrency and reserved query embedding capacity; forbid local/fake defaults.
- [ ] Run the same auth/upload/job/deletion/reconnect suites and real-model parity/quality evaluation.
- [ ] Verify database/broker/Redis/object/vector HA/recovery, independent journal durability, current-ledger restore and writer fencing.
- [ ] Exercise immutable release/migration/canary/rollback and production observability/secret rotation.

Exit: deployment works on representative hardware; code changes should be isolated to demonstrated compatibility/performance gaps, not wholesale domain rewrites. Model/index changes require explicit evaluation/migration.

## 10. Phase 8: Future production capacity and release (C)

- [ ] Benchmark components and real GPU token throughput before replica sizing.
- [ ] Run the workload profiles in [CAPACITY_PLAN.md](CAPACITY_PLAN.md), separating submissions, completed answers, polling and cache hits.
- [ ] Measure target-rate sustained/soak/burst/fault tests, queue stability, latency, isolation, answer quality, storage/WAL/backup costs and retention cleanup.
- [ ] Meet declared production SLOs, semantic targets and measured RPO/RTO; do not infer HA/capacity from manifests, mocks or a laptop test.
- [ ] Approve release for a specific environment; record achieved profiles or unresolved blockers and avoid unsupported portfolio claims.

Exit C: production-readiness and capacity assertions are backed by actual evidence. Deferring C for lack of hardware does not invalidate A/B.

## 11. Commit and testing strategy

Commit coherent implementation steps and their meaningful tests together. Unit tests use fakes; integration tests use isolated real local services; actual-model tests are opt-in and clearly labeled; target-rate/HA tests run later on representative resources. Keep application/domain logic independent of hardware, vendor SDKs and deployment addresses through narrow adapters, without building unnecessary microservices. Re-run affected checks when code/contracts change; re-evaluate model/index/topology changes before related claims.
