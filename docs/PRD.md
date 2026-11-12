# Product Requirements Document: AI PDF Chatbot

Status: production architecture baseline; not implemented or capacity-certified
Version: 2.0
Date: 2026-11-13

## 1. Purpose and decisions

Build a multi-user application that answers questions about uploaded text-based PDFs with source excerpts and original PDF page numbers. The architecture must support independent scaling, durable processing, strict document isolation, and operable production releases.

Main stack: **Python, Ollama, Qwen3 4B, LlamaIndex, ChromaDB, FastAPI, Streamlit**. PostgreSQL is the selected application database. Additional infrastructure supports this stack; it does not replace it.

The user-confirmed traffic target is **1,000–5,000 requests per second (RPS)**. This is a capacity objective, not a measured capability. The endpoint mix, model input/output lengths, corpus size, number of browser sessions, latency objectives, hosting, and budget remain to be specified before production sizing. Do not reinterpret RPS as concurrent users or quietly assume most requests are cheap status reads. [CAPACITY_PLAN.md](CAPACITY_PLAN.md) defines the separate workload profiles and release gates.

The earlier single-user localhost scope and 15-day delivery target are superseded. Local development remains supported on the Mac; production capacity must be tested on representative infrastructure. No paid model API is required, but production compute, storage, networking, and operations are not assumed free.

## 2. Document ownership

[TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md) owns service and API contracts. [TECH_STACK.md](TECH_STACK.md) owns technology choices. [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) owns delivery order. [CAPACITY_PLAN.md](CAPACITY_PLAN.md) owns sizing and performance evidence. [PROJECT_IDEA.md](PROJECT_IDEA.md) summarizes the current scope. Update affected documents together when scope changes.

## 3. User experience

1. Sign in using the configured identity provider.
2. Upload a PDF and observe processing status without blocking other interactions.
3. Select ready documents owned by the current user.
4. Submit a self-contained question and see queued/running/completed/failed status.
5. Read the answer and expand verifiable filename/page/excerpt citations.
6. Reconnect and recover recent request results without resubmitting work.
7. Delete a document; immediately lose search access while durable cleanup completes.

First release uses private documents per user; shared workspaces and document sharing are outside scope. The API derives ownership from authenticated identity, never from a client-supplied owner field.

## 4. Functional requirements

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| FR-01 | Validate bounded PDF uploads. | Reject non-PDF, encrypted/password-protected, oversized, over-page-limit, and entirely textless files with actionable errors; report textless pages in mixed PDFs. |
| FR-02 | Use durable ingestion jobs. | Accepted work survives API/worker restarts; retries are idempotent and partial indexes never become searchable. |
| FR-03 | Detect duplicates within an owner. | Identical bytes for one owner return the existing document; another owner's matching file reveals no information about its existence. |
| FR-04 | Persist document metadata and indexes. | Documents and recent request status/results survive application replica replacement. |
| FR-05 | Authorize every data operation. | Upload, list, detail, retrieval, download, retry, job status/results, and deletion enforce ownership; forged IDs cannot access another user's data. |
| FR-06 | Answer only from selected ready documents. | Reject empty/invalid selections; return grounded answers or explicit insufficient-evidence responses. |
| FR-07 | Return validated citations. | Supported answers include server-resolved filename, 1-based original PDF page index, and exact supplied excerpt; invalid model source IDs are not displayed. |
| FR-08 | Support reconnectable requests. | UI can recover recent job status and results after reconnect; logout clears browser/session data and access tokens. |
| FR-09 | Delete safely across services. | Once deletion is accepted, new retrieval/result reads exclude the document; eventual file/vector/result cleanup is tracked and retried. |
| FR-10 | Apply quotas and overload handling. | Per-user and global limits are enforced across replicas; saturation returns a retryable response rather than unbounded queues. |
| FR-11 | Treat PDF instructions as untrusted content. | Model has no action tools; adversarial evaluation checks that document instructions do not override the question or system rules. |
| FR-12 | Explain limitations. | UI explains no OCR, independent questions, PDF-index page numbers, queue state, retention, and transient service errors. |
| FR-13 | Provide operational visibility. | Operators can inspect sanitized metrics, audit events, job failures, readiness, and recovery procedures without default access to user content. |

## 5. Product boundaries

Included: authentication, private per-user PDFs, local/self-hosted generation, distributed durable processing, selected-document RAG, reconnectable short-lived request results, deletion, quotas, monitoring, deployment automation, backup/restore, and release evidence.

Deferred product features: OCR, complex table/chart reconstruction, semantic duplicate detection, shared workspaces, persistent conversational memory, history-aware question rewriting, fine-tuning, and autonomous agents. Recent request persistence is for reconnect/retry reliability, not indefinite chat storage. English text is the initial evaluation language. Model output can be wrong even when citation identifiers are valid; human evaluation remains necessary.

## 6. Nonfunctional requirements

| ID | Requirement | Release evidence |
| --- | --- | --- |
| NFR-01 | Self-hosted model processing. | No remote model fallback or paid model API dependency; control-plane identity/update/monitoring network use is documented separately. |
| NFR-02 | Authentication and data isolation. | API token validation, ownership/filter tests, cache-isolation tests, TLS, private service networking, least-privilege secrets, and sanitized logs pass. |
| NFR-03 | Capacity target of 1,000–5,000 RPS. | Production-like tests report offered/accepted/completed RPS, request mix, latency, errors, queues, corpus size, and inference tokens/second. A queued request is not a completed answer. |
| NFR-04 | Durable recovery. | Worker death, broker outage, duplicate delivery, and partial storage failure tests preserve accepted jobs or expose explicit recoverable failure. |
| NFR-05 | Reproducible delivery. | Locked dependencies, immutable images, versioned migrations, staging, automated checks, rollback, and model/index identities are documented and exercised. |
| NFR-06 | Bounded resource use. | Enforce request/file/token limits, admission quotas, bounded pools, job deadlines, and isolated PDF processing. |
| NFR-07 | Recovery and retention. | Encrypted backups and a restore drill demonstrate a proposed RPO of 1 hour and RTO of 4 hours; deletion tombstones are reapplied before restored data is exposed. |
| NFR-08 | Operational readiness. | Dashboards, alerts, runbooks, readiness/liveness, and a named operational owner exist before release. |

RPO/RTO are initial project targets, not measured guarantees. Availability and latency SLOs must be agreed with a concrete workload and infrastructure budget before release; unresolved SLOs block capacity certification.

## 7. Quality and acceptance

Maintain a tuning dataset separate from a frozen, versioned release set of at least 100 cases: 80 answerable and 20 unsupported. Include direct facts, paraphrases, multi-passage questions, conflicts, misleading instructions, blank-page numbering, and selection isolation. Initial release targets: at least 90% of answerable cases have correct supported answers and expected evidence; at least 95% of unsupported cases abstain; every emitted citation resolves to a supplied authorized excerpt. These are proposed acceptance targets, not measurements. Access-control and deletion tests require zero failures.

Other release gates: no unauthorized cross-user results; no lost accepted jobs in fault tests; deletion remains effective across retries and restore; setup and rollback drills pass; critical exploitable findings are resolved; relevant dependency/model licenses are reviewed; the exact capacity profile and SLOs pass on representative resources. A 20-question development smoke set may still be useful, but is not production certification.

## 8. Open decisions and release scope

Before sizing/signoff, record endpoint mix (including a 100% chat scenario), prompt/output lengths, data volume, upload rate, session count, latency SLOs, availability window, retention policy, provider/region, GPU budget, identity provider, and the supported Chroma deployment. Measure Streamlit's session and upload behavior at target scale. If any selected component cannot meet the profile, record the blocker and request an explicit stack change; do not label the system ready by bypassing that component in tests.
