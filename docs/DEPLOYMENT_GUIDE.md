# Local-to-GPU Deployment and Operations Guide

Status: planned runbook and acceptance contract; no deployment executed
Version: 1.0
Date: 2026-11-13

## 1. Scope

Move the locally implemented application to private production infrastructure without rewriting its API, document lifecycle, RAG logic, or authorization. Local portfolio completion requires authored/tested local artifacts; owning GPU servers is not a prerequisite. A real production launch and capacity certification require resources and separate operational verification.

The main stack and PostgreSQL remain unchanged. Infrastructure versions/providers and replica counts are selected after measuring a representative workload. No cloud resources, credentials, spending, or deployment are created by this plan.

## 2. What changes and what stays the same

| Concern | Local | GPU deployment |
| --- | --- | --- |
| API/UI/workers | Single instances; same service interfaces | Independently replicated immutable images. |
| Inference | Explicit deterministic fake or actual native/CPU Ollama | Actual pinned Ollama/Qwen3 and Nomic on suitable private hardware; fake mode forbidden. |
| Query/ingestion embeddings | One serialized endpoint with fair scheduling | Dedicated query capacity or guaranteed scheduler reservations, separate ingestion budget. |
| Files | Private versioning-capable local object service | Private durable object service with encryption and lifecycle/version policies. |
| Metadata/jobs | Local PostgreSQL/RabbitMQ/Redis | Tested HA/recovery services, bounded pools, protected network. |
| Vector search | Single Chroma service | Supported service/distributed topology sized and operated for actual corpus/QPS. |
| Identity | Local OIDC provider; isolated fixture issuer only in tests | Chosen provider/access-token audience, managed secrets and rotation. |
| Journal | Separate local namespace simulates protection | Independent durability/credentials outside database rollback boundary. |
| Deployment | Compose/native profiles | Kubernetes/Helm topology, GPU devices/node scheduling, ingress and autoscaling. |

Hardware-only changes do not require business-logic changes or automatic reindexing. A changed embedding identity/dimension/chunking configuration does require a versioned reindex. Even when identities stay the same, run CPU/GPU output/quality checks; do not expect identical floating-point output or assume parity without testing.

## 3. Artifacts to author locally

- Locked Python dependencies, versioned SQL migrations, and multi-platform build strategy for developer and target architectures.
- Immutable API/UI/worker/router images; separate provider/runtime image for Ollama. Verify target architecture/native PDF/vector dependencies; do not assume Mac-built binaries work on a Linux server.
- Compose development/integration profiles, safe example configuration, private secrets references, and documented shutdown/reset behavior.
- Helm/manifests for application and GPU pools, resource requests/limits, GPU discovery/plugin/runtime prerequisites, model volumes/warmup, probes, draining and topology/disruption settings.
- Ingress with TLS/WebSockets/affinity, private network policies, service authentication/access rules, bounded timeouts/body limits, distributed quotas and connection budgets.
- Staging migration, smoke, canary/promotion, rollback, backup/restore and retention procedures with exact executable commands once implemented.

Render/validate manifests locally and test containers where feasible. Mark real GPU scheduling, HA, external TLS/provider integration and target-rate benchmarks unverified until exercised. A valid manifest is not a working deployment.

## 4. Migration sequence when resources become available

1. Record workload/SLOs, hardware/budget, provider/region, identity, Chroma topology, retention and journal guarantees in the decision log.
2. Provision isolated staging; restrict storage/model/broker/database networks. Install tested GPU drivers/runtime and confirm Ollama sees the intended device before claiming GPU acceleration.
3. Preload/pin Qwen3 and Nomic artifacts; configure private endpoint inventory, model limits and warmup probes. Do not expose Ollama directly to the public internet.
4. Build/deploy images for the target platform and apply backward-compatible migrations as a controlled task. Reject development issuers, fake models, placeholder secrets and developer storage endpoints.
5. Migrate permitted data through verified object identities and database consistency checkpoints, or start clean with fixtures. Never merge fake indexes into real ones. Preserve owner/identity mapping and replay current deletion intents before opening access.
6. Run authenticated upload/job/retrieval/deletion/reconnect smoke tests, frozen semantic evaluation, token-expiry/key-rotation checks, and component tests.
7. Measure safe model concurrency/token throughput and query-embedding reservations. Configure warm headroom and admission budgets from evidence, not local guesses.
8. Run the capacity/fault profiles and report actual achieved throughput. Only then can the production environment claim the measured workload/SLO.
9. Canary a limited audience, watch metrics, then promote or roll back. A future production launch requires a named operational owner and explicit environment-specific release decision.

## 5. Deployment and rollback safety

Gracefully stop admission/drain old processes; do not terminate acknowledged work without durable rescheduling. Outbox/lease fencing and attempt-specific vector/result namespaces prevent retries from corrupting winning work. UI reconnect discovers jobs through the API; sticky sessions do not make memory durable.

Use schema expand/contract so the previous image can run during rollback. Revert images/configuration through tested procedures; never automatically run destructive database down migrations. Retain previous model/index configurations long enough for rollback. For index/model changes, build a new isolated version, evaluate it, atomically switch the published pointer, and garbage-collect only after rollback grace and reader safety checks.

## 6. Recovery and deletion

Back up PostgreSQL with tested restore/PITR, immutable document objects and required versions, Chroma snapshot/rebuild identity, model/index configuration, and encryption-key recovery material. Keep deletion intents independently durable and protected against rollback/history loss. The proposed production RPO/RTO targets remain unverified until a timed drill on real resources.

Restore with user traffic and job dispatch closed. Fence old writers, recover storage/database/vector state, replay the current independent journal through a verified cutover checkpoint, invalidate affected jobs/results, reconcile objects/versions, and verify no acknowledged deletion can reappear. If journal coverage, credentials/keys, or replay cannot be verified, readiness remains closed. Then resume/drain jobs idempotently and open traffic only after checks pass.

For versioned stores, physical cleanup must enumerate/delete applicable noncurrent versions and abandoned multipart uploads; adding delete markers alone does not remove stored bytes. Respect the disclosed backup retention window and protect minimal deletion metadata beyond every restorable backup plus recovery margin. No claim of immediate backup erasure is made.

## 7. Incident and maintenance checklist

Monitor API/job latency, accepted/completed rates, queue age, query/ingestion embedding wait, GPU memory/token rates, connection pools, vector errors, storage/cleanup lag, journal durability, backups and auth failures. Track cold-start/model-loading delays before autoscaling decisions. Sanitize logs/traces and avoid high-cardinality content identifiers in metrics.

Provide runbooks for model outage, saturated queues, broker/database/Redis failure, vector/object errors, storage full, failed deletion/journal writes, token/key rotation and failed release. Actions are bounded: close new admission when safety/capacity is unknown, preserve accepted job state, avoid retry storms, and resume only after readiness checks. Test dependency/model upgrades in staging and rerun affected correctness/quality/capacity checks.

## 8. Launch evidence

Before a real production launch: concrete workload/SLO/budget decisions, actual identity/storage/model integration, security/correctness results, GPU parity/quality evidence, capacity report, fault/restore/rollback drills, HA topology evidence, monitoring/alerts, key/secret recovery, and an operational owner. Before local portfolio completion: local evidence plus clearly labeled pending deployment checks; no hardware purchase is required.
