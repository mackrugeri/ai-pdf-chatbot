# Implementation Plan

Version 4.0 | 2026-11-13 | Planned work; nothing marked implemented by documentation

## 1. Working scope

Implement the [PRD](PRD.md) against the [technical design](TECHNICAL_DESIGN.md) and fixed [stack](TECH_STACK.md). Local development requires no dedicated GPU. Start with deterministic tests and staged single-instance services, then optional real CPU/native Ollama. Preserve the production interfaces and correctness; do not replace durable jobs/auth with throwaway local-only shortcuts.

The first deliverable is a reproducible local portfolio project. Later deployment files/CI/CD/Terraform/GPU resource configuration are added when staging/production is needed. Actual production readiness/HA/RPS proof is a separate later milestone, not a prerequisite for coding. No fixed 15-day promise, cloud provisioning or infrastructure spending is authorized.

## 2. Ordered milestones

| Step | Implementation work | Completion check |
| --- | --- | --- |
| 1. Foundation | Python/uv lock, modules, typed settings, safe examples/ignores, API schemas/errors/probes, adapter interfaces, Ruff/pytest; verify package/platform compatibility and licenses. | Clean environment runs skeleton and unit tests; no hardcoded hardware/addresses or leaked secrets. |
| 2. Local services and identity | Incremental Docker/Compose profiles for PostgreSQL/RabbitMQ/Redis/Chroma/private S3-compatible service; local OIDC provider, actual API-audience access tokens, ownership mapping; migrations/bounded pools. | Authenticated UI/API vertical slice and real local service tests; wrong-owner/expired/forged tokens rejected. Production config rejects fakes/test defaults. |
| 3. PDF ingestion input | Quota reservations, owner duplicates/idempotency, version-pinned verified staging, immutable final promotion, parser isolation, page-aware chunks/counts and source metadata. | Invalid/over-limit/encrypted/textless cases fail; URL overwrite/duplicate/crash tests preserve exact accepted bytes/page numbers and clean orphans. |
| 4. Durable indexing | Job/receipt/outbox schema, publisher confirms, separate workers, attempt leases/heartbeats/deadlines/retries, actual broker adapter and bounded embeddings. | API/worker/broker crashes and duplicate delivery recover accepted jobs; incomplete/loser attempts stay invisible. |
| 5. Attempt-safe vectors | Attempt-specific Chroma/artifact namespaces, verified counts and atomic winner pointer, version/fingerprint checks, scoped reconciler cleanup. | A paused loser resuming writes/cleanup cannot mutate/delete winner data; no broad cleanup races. |
| 6. Retrieval and answering | Owner/selected-version/attempt filtering, query-embedding reservations/fair local scheduling, full-prompt budgets, model adapters, grounded structured answers/citations, abstention/format repair. | Fakes test orchestration; opt-in actual Qwen3/Nomic runs separately establish semantic evidence. Ingestion flood cannot consume all query capacity. |
| 7. Results, UI and lifecycle | Encrypted result objects, recent paginated jobs/detail, bounded polling/reconnect, safe source display, cancel/retry controls, terminal retention, active-input safety and separate receipts. | Empty-session reconnect restores owner jobs; cursor/expiry/user-isolation tests pass; expiry does not resubmit work or erase active inputs. |
| 8. Deletion and recovery | Journal-first intents, tombstones/cancellation, version/attempt/file/result/cache cleanup, protected replay/checkpoints, writer fencing and closed restore. | Deleting during generation/retry cannot republish; restoring an older backup replays newer deletions; missing journal fails closed. Local independence limits are documented. |
| 9. Portfolio completion | Verified startup/test/reset commands, permitted fixtures/demo, architecture diagram, test results, actual model/config identity and honest evidence status. | Reproducible local project; separate fake/real evidence; no unsupported production-capacity claim. |

Start each service only when needed; keep optional full monitoring/HA profiles off by default. Local real inference uses one global operation slot and conservative context/batches; a fake adapter is explicit, not an automatic fallback. If real models cannot run locally, the software work can continue but real-quality evidence stays pending.

## 3. Required verification

- Unit/contract tests: validation, chunking/page gaps, state transitions, source markers, structured model errors and fake/Ollama interface parity.
- Real local integration: database migrations/ownership, object versions/checksums/policies, broker/outbox/retries, Redis admission, Chroma filtering/attempt isolation and actual OIDC login/token validation.
- Lifecycle/fault tests: duplicate/completion/idempotency races, stale workers, timeout with unknown execution, cancellation/deletion, session loss, payload expiry, journal/DB partial failure, restore and cleanup.
- Actual-model quality: keep tuning separate from a frozen 100-case set (80 answerable/20 unsupported); targets from PRD apply only to real runs. Record not-run/skipped checks honestly.
- Security/privacy: no cross-user results, unsafe HTML or content/credential logging; isolated destructive test stores, bounded parser/model/network resources, no unguarded test identities in production.

Commit coherent changes with meaningful tests. Keep tests fake by default and real-model checks opt-in; tests cannot silently download models or call paid APIs. Update the relevant contract when implementation changes a design decision, rather than adding another overlapping document.

## 4. Later staging/production milestone

When resources are available, choose workload/SLOs, provider/region/GPU budget, production OIDC/object/journal and supported Chroma topology. Author/verify GitHub Actions deployment stages, Terraform, target-platform Docker images and Kubernetes/Helm configuration; keep hardware/network/resource settings out of business logic.

Preload pinned models, verify actual GPU execution and separate query/ingestion capacity, run the same correctness/auth suites, then real-model parity/quality, database/broker/storage HA, restore/rollback and actual load tests. Use schema expand/contract and versioned indexes for rollback. Set monitoring/alerts/runbooks and an operational owner before release.

Report offered/admitted/completed RPS separately, including browser/polling overhead, latency, queues, token rates, retention costs and failure recovery. Measure representative 1,000–5,000 RPS profiles only on suitable resources. No GPU benchmark, HA guarantee, RPO/RTO or throughput claim is earned by a diagram, local fake test or authored manifest.

## 5. Decisions and current status

Fixed now: main stack/PostgreSQL, private ownership, durable jobs/outbox, immutable uploads, attempt-safe vectors, grounded citations, query scheduling, journal-protected recovery and hardware-neutral adapters.

Resolve during foundation: tested versions, local OIDC/object service compatibility, exact configuration/startup commands and migration/index/idempotency constraints. Resolve at deployment: providers/resources, production SLO/budget, supported Chroma topology, HA/retention and capacity. These future choices do not block local implementation.

Current evidence: documentation reviewed; no application implementation, installation, real-model demo, deployment or performance test has been executed in this documentation task. Next checkpoint is the tested authenticated local vertical slice, not more overlapping planning files.
