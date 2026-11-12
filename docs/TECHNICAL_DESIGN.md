# Technical Design Document: AI PDF Chatbot

Status: implementation baseline, version 1.0
Date: 2026-11-12
Requirements: [PRD.md](PRD.md)
Technology rationale: [TECH_STACK.md](TECH_STACK.md)

## 1. Design approach

Main stack: **Python, Ollama, Qwen3 4B, LlamaIndex, ChromaDB, FastAPI, Streamlit**. Supporting dependencies and tools are detailed in [TECH_STACK.md](TECH_STACK.md).

Use a Streamlit UI backed by a single FastAPI process. Keep PDF extraction, embeddings, retrieval, generation, and persistence behind separate service interfaces. PostgreSQL owns document lifecycle state; ChromaDB stores chunk text, vectors, and source metadata; the filesystem stores uploaded PDFs. Ollama provides local embedding and generation models. LlamaIndex coordinates chunking/retrieval adapters without owning a second authoritative metadata database.

```text
Streamlit -> FastAPI -> Document service -> PDF extraction -> Chunking
                    |                                      -> Ollama embeddings
                    |                                      -> ChromaDB
                    |                -> PostgreSQL + local PDF files
                    |
                    -> Answer service -> selected ready IDs -> ChromaDB retrieval
                                      -> bounded excerpts -> Ollama generation
                                      -> citation validation -> response
```

Backend is the sole storage owner. UI never reads PostgreSQL, ChromaDB, or uploaded files directly. Use one backend worker; in-process jobs and coordination locks are not designed here for multiple API workers.

## 2. Configuration and initial limits

All values below are planned starting defaults, adjustable after measurement, not verified model or library specifications.

| Setting | Initial value |
| --- | --- |
| Backend / UI binding | `127.0.0.1:8000` / `127.0.0.1:8501` |
| Ollama URL | `http://127.0.0.1:11434` |
| Answer / embedding model | `qwen3:4b` / `nomic-embed-text` |
| Maximum upload | 20 MiB per file, enforced while reading |
| Maximum pages | 300 per PDF |
| Maximum extracted text | 2 million characters per document |
| Question length | 1–2,000 characters after trimming |
| Selected documents | 1–10 unique IDs |
| Chunk target / overlap | 1,200 / 200 characters, bounded to one page |
| Retrieval / context | top 6 candidates; at most 4,000 context characters |
| Model context / output budget | request 8,192 context tokens; at most 1,024 output tokens |
| Model calls | one embedding/generation operation at a time |
| Upload processing | one ingestion job at a time; at most 3 queued jobs |
| Model request timeout | 180 seconds; return a retryable service error |

Use a tested tokenizer or conservative token budget check on the complete prompt before generation. Character limits do not guarantee token counts: drop lowest-ranked excerpts until the full prompt fits with output headroom; reject a question that cannot fit. Verify the selected Ollama model supports the requested settings during setup. Include model identity, embedding dimension, chunking settings, and index schema in an index fingerprint.

## 3. Modules and repository layout

```text
app/
  main.py                 # lifespan, dependency wiring, API routers
  config.py               # validated environment configuration
  api/                    # documents, chat, health routes
  schemas/                # request, response, and internal models
  services/               # extraction, chunking, ingestion, retrieval, answering
  storage/                # PostgreSQL repository, Chroma adapter, local files
ui/streamlit_app.py
tests/fixtures/
evaluation/questions.json
data/                     # ignored: uploads/, chroma/; PostgreSQL data is managed separately
```

Use dependency injection for storage and model clients so automated tests use temporary directories and deterministic fakes. Do not add unnecessary abstractions beyond these boundaries.

## 4. Persistence contract

### PostgreSQL documents

Run PostgreSQL locally and connect through a configured `DATABASE_URL` using Psycopg 3 with a small bounded connection pool. Use a dedicated application database and role with only the permissions required for that database. Keep credentials in local environment configuration and out of Git and logs. Store PostgreSQL data outside the repository using the database service's managed data directory. Use versioned SQL migrations; run them explicitly during setup and upgrades. Verify database readiness in `/health`; database outages disable ingestion and chat with actionable service errors.

Store `id` (UUID primary key), `original_filename`, `stored_filename`, `sha256` (unique), nullable `page_count`, `textless_page_count`, `chunk_count`, `status`, nullable `error_code` and `error_message`, `created_at`, `updated_at`, and `index_fingerprint`. Timestamps use UTC ISO 8601. Status values: `pending`, `processing`, `ready`, `failed`, `deleting`.

A single settings record stores schema version and index fingerprint. Use parameterized queries and short transactions; never hold a SQL transaction open during model calls. Create a small migration/version mechanism from the start rather than silently changing existing schemas.

### Chroma chunks

Each record has a deterministic chunk ID derived from document ID, page index, chunk index, and fingerprint; embedding; chunk text; and metadata containing document ID, original filename, original 1-based page number, and chunk index. Use one persistent collection per active fingerprint. PostgreSQL readiness remains the authoritative visibility gate.

### Files

Store uploads as `<uuid>.pdf` beneath the configured data directory. Treat original filenames as display strings only and escape them in the UI. Resolve and check storage paths beneath the upload root. Use a temporary file during bounded streaming, then atomically move it on acceptance. Never accept client-supplied filesystem paths.

## 5. Ingestion and lifecycle

1. Check queue capacity and stream upload with a byte limit; compute SHA-256.
2. Verify the file opens as PDF and reject encrypted/password-protected files. Check page count before processing all text.
3. Under a short transaction, create the pending record or return an existing hash match. Remove the duplicate temporary file. Existing failed records are returned with instructions to delete and re-upload.
4. Move accepted file into controlled storage and enqueue its ID. Return `202`. If storage/enqueue fails, mark failed and clean up temporary state.
5. Worker marks processing and extracts page text, enforcing total text size. Preserve original page indices; count textless pages. Reject fully textless documents.
6. Normalize whitespace conservatively. Create deterministic overlapping character chunks within each page, preferring paragraph boundaries and ensuring the next chunk advances. Do not cross page boundaries.
7. Embed bounded batches with truncation disabled where supported; fail clearly if an input exceeds the model limit. Persist chunks with idempotent upserts.
8. Verify expected chunk count, then mark ready in PostgreSQL. Only ready IDs are eligible for retrieval.
9. On failure, exclude the document immediately, delete partial vectors, and mark failed. Persist cleanup errors for startup reconciliation; filtering must exclude failed records even if cleanup fails.

At startup, mark stale pending/processing records failed with `INGESTION_INTERRUPTED` and clean partial vectors. Retry pending deletions. Reconcile orphan files/vectors against document IDs without touching unrelated paths. In-process jobs do not survive restarts; failed documents require deletion and re-upload. Do not silently rebuild incompatible indexes: report `INDEX_INCOMPATIBLE`, block indexing/chat, and provide a documented explicit rebuild procedure that preserves original PDFs until the rebuild succeeds.

### Deletion and concurrency

Use one mutation lock around ingestion/deletion and a visibility lock coordinating chat with deletion. A queued or processing document returns `409 DOCUMENT_BUSY` on deletion; the user retries after completion. Deletion of ready/failed records first sets deleting, then removes vectors and file, then removes the record. Partial deletion remains deleting and excluded; repeated DELETE or startup recovery resumes it idempotently. A missing ID returns `404`.

A chat holds the visibility lock through retrieval and generation. Deletion waits for any active chat to finish; a successful DELETE guarantees no subsequent chat can use that document. Avoid holding the PostgreSQL transaction while waiting. Apply bounded waits and return a retryable busy response instead of blocking indefinitely.

## 6. Retrieval and answer generation

Validate that every requested document exists, is ready, and has a compatible fingerprint. Never interpret an empty selection as all documents. Embed the question with the active embedding model and filter retrieval by the validated IDs. Recheck returned metadata against the allowlist as defense against adapter/filter mistakes.

Retrieve up to six chunks and build a bounded context. Assign request-local source labels such as `S1` only to excerpts actually included in the prompt. Use server-owned filename/page metadata for references; model text never supplies authoritative source metadata. Do not use a universal similarity cutoff or label similarity as answer confidence without evaluation.

System instructions require answers from supplied evidence, explicit abstention when evidence is insufficient, citations for supported claims, and treating document text as untrusted data. Delimit excerpts as data. No code execution, browsing, filesystem, or other action tools are available to the model. Session history is not sent to the backend in the MVP; every question is independent.

Ask the model for a validated structured result with `answer`, `source_ids`, and `insufficient_evidence`; include inline `[S1]` markers in supported answers. Verify the response schema, source IDs, and inline markers against supplied sources. Supported responses require at least one valid citation. Retry once on invalid structure/citations, then return `502 INVALID_MODEL_RESPONSE`; never present unvalidated citations as evidence. If retrieval returns no chunks, respond with a deterministic insufficient-evidence message without generation. An abstention returns no citations and must not contain unsupported factual claims.

Return only cited sources, deduplicated, including exact supplied excerpts. Identifier checks cannot establish semantic support; manual evaluation is required. The insufficient-evidence field is not calibrated confidence.

## 7. API contract

All endpoints return JSON except multipart upload. Invalid field schemas return `422` in the common error envelope. Disable cross-origin access by default; the Streamlit server calls the API locally.

| Method and route | Request | Success |
| --- | --- | --- |
| `GET /health` | none | `200`: app/storage health, Ollama reachability, configured model availability, index compatibility, per-capability readiness |
| `POST /documents` | multipart `file` | `202`: new Document; `200`: existing duplicate Document with `duplicate: true` |
| `GET /documents` | none | `200`: `{documents: [Document]}` newest first |
| `GET /documents/{id}` | UUID path | `200`: Document |
| `DELETE /documents/{id}` | UUID path | `204` on completed deletion |
| `POST /chat` | `{question: string, document_ids: UUID[]}` | `200`: ChatResponse |

`Document`: id, original_filename, status, nullable page_count, textless_page_count, chunk_count, nullable error `{code,message}`, created_at, updated_at. Upload responses wrap this as `{document, duplicate}`. Do not expose internal storage paths or raw exception messages.

`ChatResponse`: answer string, insufficient_evidence boolean, sources array of `{source_id, chunk_id, document_id, filename, page_number, excerpt}`, request_id. UI renders answer text safely and presents sources as expandable text.

Error envelope: `{error: {code, message, retryable}, request_id}`. HTTP mappings: `413` upload too large; `415` unreadable/non-PDF input; `422` invalid input, encrypted/textless/over-limit PDF if detected synchronously; `404` unknown document; `409` not ready, busy, or index incompatible; `429` queue/concurrency capacity exceeded; `503` storage/model service unavailable; `504` model timeout; `502` invalid model response. Asynchronous ingestion errors appear on the Document instead of changing the completed upload HTTP response. `/health` returns `503` if required storage cannot be opened; model downtime is represented in capability readiness without hiding metadata/delete availability.

Example chat request:

```json
{"question":"What is the warranty period?","document_ids":["5bbdbaca-b1ec-4c7f-b054-63e33bc20d1a"]}
```

Example supported response:

```json
{"answer":"The warranty period is two years [S1].","insufficient_evidence":false,"sources":[{"source_id":"S1","chunk_id":"example-chunk","document_id":"5bbdbaca-b1ec-4c7f-b054-63e33bc20d1a","filename":"manual.pdf","page_number":3,"excerpt":"The warranty period is two years."}],"request_id":"example-request"}
```

## 8. UI behavior

Sidebar shows readiness, upload controls, per-document status, textless-page notices, document selection, and deletion. Poll processing status approximately every two seconds without triggering duplicate uploads on rerun. Disable asking with no ready selection and prevent repeated submissions while a request is active. Keep session history with each answer's source snapshot. Deleting a document removes history entries referencing it from the current UI session to avoid stale source displays. Clear-history affects no stored documents. Render PDF excerpts and model output as untrusted text; do not enable unsafe HTML.

## 9. Reliability, privacy, and observability

Use one shared model-call semaphore for embedding and generation; release/unload models where the tested Ollama integration supports it to reduce overlapping memory use. Set explicit timeouts and bounded waits. Do not automatically retry a timed-out generation; it may still be finishing locally. Keep the application single-user and localhost-only.

Log request IDs, document IDs, durations, counts, lifecycle transitions, and sanitized error codes. Avoid PDF text, original filenames, questions, answers, and prompts in default logs. Ignore data, environment secrets, and generated logs in Git. Do not add telemetry or remote model fallbacks. Record dependency and model licenses before distribution.

## 10. Verification and tradeoffs

Map tests to PRD requirement IDs. Unit tests cover page-aware chunking, validation, prompt/citation handling, and state transitions. API tests use fake model clients, an isolated test database, and temporary file/vector stores. Storage integration tests exercise real local PostgreSQL/Chroma behavior using an isolated test database and temporary vector directories. Never run destructive tests against the development database. Manual local-model checks evaluate semantic grounding, prompt injection cases, offline operation, memory, and latency against the fixed evaluation set.

Tradeoffs: page-bounded chunks simplify citations but can split a multi-page concept; vector-only retrieval is simpler but may miss exact identifiers; in-process ingestion avoids another service but needs restart recovery; serialized model calls reduce memory pressure but limit throughput. These are acceptable for the local MVP. OCR, reranking, persistent conversations, distributed workers, and deployment remain outside this design.
