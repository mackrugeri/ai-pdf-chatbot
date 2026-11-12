# Product Requirements Document: AI PDF Chatbot

Status: production architecture baseline; not implemented or capacity-certified
Version: 3.0
Date: 2026-11-13

## 1. Purpose and decisions

Build a multi-user application that answers questions about uploaded text-based PDFs with source excerpts and original PDF page numbers. The architecture must support independent scaling, durable processing, strict document isolation, and operable production releases.

Main stack: **Python, Ollama, Qwen3 4B, LlamaIndex, ChromaDB, FastAPI, Streamlit**. PostgreSQL is the selected application database. Additional infrastructure supports this stack; it does not replace it.

The user-confirmed traffic target is **1,000–5,000 requests per second (RPS)**. This is a capacity objective, not a measured capability. The endpoint mix, model input/output lengths, corpus size, number of browser sessions, latency objectives, hosting, and budget remain to be specified before production sizing. Do not reinterpret RPS as concurrent users or quietly assume most requests are cheap status reads. [CAPACITY_PLAN.md](CAPACITY_PLAN.md) defines the separate workload profiles and release gates.

The earlier single-user localhost scope and 15-day delivery target are superseded. Local development remains supported on the Mac; production capacity must be tested on representative infrastructure. No paid model API is required, but production compute, storage, networking, and operations are not assumed free.

## 2. Delivery scope: local portfolio first, GPU deployment later

The current deliverable is a locally buildable portfolio application with production-oriented service boundaries and correctness, not an operating 5,000-RPS GPU deployment. No dedicated GPU, paid infrastructure, Kubernetes cluster, or measured production capacity is required to begin or finish the local engineering milestone. Keep the distributed contracts while running one instance of each needed service.

Use deterministic model fakes for routine development/tests and optional real Qwen3 4B/Nomic inference through local Ollama on CPU or available native acceleration. Fake inference must be visibly labeled and isolated from real indexes; it proves software behavior, not answer quality. A real-model smoke/evaluation run is required before describing the demo as answering PDFs with Qwen3; if local resources cannot support it, report that evidence as pending rather than substitute a model silently.

Three separate outcomes apply: (A) local portfolio implementation and test evidence; (B) deployment artifacts and a documented GPU migration path, with hardware-dependent checks explicitly pending; (C) production readiness/capacity verified on representative provisioned resources. Production-only sizing/HA/SLO decisions do not block A. No deployment or spending is requested by this plan.

See [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md), [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md), [DECISION_LOG.md](DECISION_LOG.md), and [DOCUMENTATION_REVIEW.md](DOCUMENTATION_REVIEW.md).

## 3. Document ownership

[TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md) owns service and API contracts. [TECH_STACK.md](TECH_STACK.md) owns technology choices. [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) owns delivery order. [CAPACITY_PLAN.md](CAPACITY_PLAN.md) owns sizing and performance evidence. [PROJECT_IDEA.md](PROJECT_IDEA.md) summarizes the current scope. Update affected documents together when scope changes.

## 4. User experience

1. Sign in using the configured identity provider.
2. Upload a PDF and observe processing status without blocking other interactions.
3. Select ready documents owned by the current user.
4. Submit a self-contained question and see queued/running/completed/failed status.
5. Read the answer and expand verifiable filename/page/excerpt citations.
6. Reconnect and recover recent request results without resubmitting work.
7. Delete a document; immediately lose search access while durable cleanup completes.

First release uses private documents per user; shared workspaces and document sharing are outside scope. The API derives ownership from authenticated identity, never from a client-supplied owner field.

## 5. Functional requirements

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| FR-01 | Validate bounded immutable PDF uploads. | Reject non-PDF, encrypted/password-protected, oversized, over-page-limit, and entirely textless files; report textless pages in mixed PDFs. Bind accepted work to verified immutable bytes so reusing an upload target cannot change the indexed/downloaded PDF. |
| FR-02 | Use durable ingestion jobs. | Accepted work survives API/worker restarts; retries are idempotent and partial indexes never become searchable. |
| FR-03 | Detect duplicates within an owner. | Identical bytes for one owner return the existing document; another owner's matching file reveals no information about its existence. |
| FR-04 | Persist document metadata and indexes. | Documents and recent request status/results survive application replica replacement. |
| FR-05 | Authorize every data operation. | Upload, list, detail, retrieval, download, retry, job status/results, and deletion enforce ownership; forged IDs cannot access another user's data. |
| FR-06 | Answer only from selected ready documents. | Reject empty/invalid selections; return grounded answers or explicit insufficient-evidence responses. |
| FR-07 | Return validated citations. | Supported answers include server-resolved filename, 1-based original PDF page index, and exact supplied excerpt; invalid model source IDs are not displayed. |
| FR-08 | Support reconnectable requests. | An owner-scoped paginated jobs API lets the UI rediscover recent jobs and recover available status/results after complete session-state loss; logout clears browser/session data and access tokens. |
| FR-09 | Delete safely across services. | Once deletion is accepted, new retrieval/result reads exclude the document; eventual file/vector/result cleanup is tracked and retried. |
| FR-10 | Apply quotas and overload handling. | Per-user and global limits are enforced across replicas; saturation returns a retryable response rather than unbounded queues. |
| FR-11 | Treat PDF instructions as untrusted content. | Model has no action tools; adversarial evaluation checks that document instructions do not override the question or system rules. |
| FR-12 | Explain limitations. | UI explains no OCR, independent questions, PDF-index page numbers, queue state, retention, and transient service errors. |
| FR-13 | Provide operational visibility. | Operators can inspect sanitized metrics, audit events, job failures, readiness, and recovery procedures without default access to user content. |

## 6. Product boundaries

Included: authentication, private per-user PDFs, local/self-hosted generation, distributed durable processing, selected-document RAG, reconnectable short-lived request results, deletion, quotas, monitoring, deployment automation, backup/restore, and release evidence.

Deferred product features: OCR, complex table/chart reconstruction, semantic duplicate detection, shared workspaces, persistent conversational memory, history-aware question rewriting, fine-tuning, and autonomous agents. Recent request persistence is for reconnect/retry reliability, not indefinite chat storage. English text is the initial evaluation language. Model output can be wrong even when citation identifiers are valid; human evaluation remains necessary.

## 7. Nonfunctional requirements

| ID | Requirement | Release evidence |
| --- | --- | --- |
| NFR-01 | Self-hosted model processing. | No remote model fallback or paid model API dependency; control-plane identity/update/monitoring network use is documented separately. |
| NFR-02 | Authentication and data isolation. | API token validation, ownership/filter tests, cache-isolation tests, TLS, private service networking, least-privilege secrets, and sanitized logs pass. |
| NFR-03 | Capacity target of 1,000–5,000 RPS. | Production-like tests report offered/accepted/completed RPS, request mix, latency, errors, queues, corpus size, and inference tokens/second. A queued request is not a completed answer. |
| NFR-04 | Durable recovery. | Worker death, broker outage, duplicate delivery, and partial storage failure tests preserve accepted jobs or expose explicit recoverable failure. |
| NFR-05 | Reproducible delivery. | Locked dependencies, immutable images, versioned migrations, staging, automated checks, rollback, and model/index identities are documented and exercised. |
| NFR-06 | Bounded resource use. | Enforce request/file/token limits, admission quotas, bounded pools, job deadlines, and isolated PDF processing. |
| NFR-07 | Recovery and retention. | Encrypted backups and a restore drill demonstrate a proposed RPO of 1 hour and RTO of 4 hours; a deletion journal protected independently of database recovery is replayed through a verified cutover point before restored data is exposed. |
| NFR-08 | Operational readiness. | Dashboards, alerts, runbooks, readiness/liveness, and a named operational owner exist before release. |
| NFR-09 | Sustainable job/result retention. | Size hot metadata, indexes, receipts, payloads, WAL/replicas, backups, and cleanup at admitted job rate; prove retention does not cause unbounded storage, block active work, or allow duplicate jobs after payload expiry. |
| NFR-10 | Hardware-portable local development. | Run the same API/worker/storage contracts without a dedicated GPU; change only validated endpoint/deployment/resource settings for GPU hosting. Fakes and real-model evidence remain clearly separated. |

RPO/RTO are initial project targets, not measured guarantees. Availability and latency SLOs must be agreed with a concrete workload and infrastructure budget before release; unresolved SLOs block capacity certification.

## 8. Quality and acceptance

Maintain a tuning dataset separate from a frozen, versioned release set of at least 100 cases: 80 answerable and 20 unsupported. Include direct facts, paraphrases, multi-passage questions, conflicts, misleading instructions, blank-page numbering, and selection isolation. Initial release targets: at least 90% of answerable cases have correct supported answers and expected evidence; at least 95% of unsupported cases abstain; every emitted citation resolves to a supplied authorized excerpt. These are proposed acceptance targets, not measurements. Access-control and deletion tests require zero failures.

Portfolio acceptance requires local integration/correctness tests, reproducible setup instructions, synthetic/permitted demo fixtures, honest model/test evidence, and a documented deployment path. The 100-case semantic quality target applies to a real-model quality report, not fake-model tests. GPU/HA/full-capacity evidence can remain pending and must be labeled as such; this does not prevent a portfolio engineering release.

Production release gates: no unauthorized cross-user results; no lost accepted jobs in fault tests; deletion remains effective across retries and restore; setup and rollback drills pass; critical exploitable findings are resolved; relevant dependency/model licenses are reviewed; the exact capacity profile and SLOs pass on representative resources. A 20-question development smoke set may still be useful, but is not production certification.

Additional regression gates: mutate an upload during/after completion and verify only the pinned bytes are indexed; reconnect with no remembered job IDs and rediscover only the authenticated owner's recent jobs; restore a backup older than an acknowledged deletion and verify current journal replay prevents resurrection; run sustained job expiry/partition cleanup and ensure idempotency receipts outlive the retry horizon. See the technical design for exact contracts.

## 9. Open decisions and release scope

Before sizing/signoff, record explicit values/selected providers and an accountable owner for each open decision: endpoint mix (including a 100% chat scenario), prompt/output lengths, data volume, upload rate, session count, latency SLOs, availability window, retention policy, provider/region, GPU budget, identity provider, supported Chroma deployment, immutable-object mechanism, independent deletion-journal protection/cutover, and job/result storage and cleanup budgets. Track them in the decision log with an owner and required milestone. GPU capacity/provider/budget/HA decisions block production certification, not local implementation; local service contracts, auth boundaries, and isolation rules must be decided for development. Do not substitute guessed values for production evidence. Measure Streamlit's session and upload behavior at target scale. If any selected component cannot meet the profile, record the blocker and request an explicit stack change; do not label the system ready by bypassing that component in tests.
