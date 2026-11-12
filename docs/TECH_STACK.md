# Technology Stack: AI PDF Chatbot

Status: planned selection, version 1.0
Date: 2026-11-12

## 1. Scope and selection principles

This document records the technologies we intend to use, their responsibilities, and what must be verified before installation. It is a design choice, not an installed dependency inventory or a compatibility certification. See [PRD.md](PRD.md) for scope, [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md) for contracts, and [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for delivery tasks.

Choose a local-first Python stack that can be learned incrementally on an Apple Silicon MacBook with 16 GB unified memory. Normal runtime must not need a paid API key or remote AI service. Keep one backend, one lightweight UI, embedded storage, and bounded model concurrency.

## 2. Selected stack

| Layer | Planned choice | Responsibility and rationale |
| --- | --- | --- |
| Language | Python 3.11 as the initial compatibility target | One language for parsing, API, RAG services, and UI; verify all dependencies before locking the supported version. |
| Environment | uv with a project `.venv` | Manage dependencies and produce a committed `uv.lock`; avoid changing system Python. |
| Model runtime | Ollama running locally | Host generation and embedding models behind a local HTTP interface. |
| Generation | `qwen3:4b`, quantized local artifact | Answer questions from retrieved excerpts; record the exact artifact/digest and measure memory during setup. |
| Embeddings | `nomic-embed-text` through Ollama | Use one embedding identity consistently for both chunks and questions. |
| PDF parsing | PyMuPDF | Extract text page by page while retaining original PDF positions. Verify licensing before distribution. |
| RAG integration | LlamaIndex with only needed adapters | Coordinate chunk/retrieval workflows; application services retain control of lifecycle, filtering, prompts, and citations. |
| Vector storage | ChromaDB in persistent local mode | Store embeddings, chunk text, and source metadata without a separate database server. |
| Metadata | SQLite through Python's standard library | Own document records, lifecycle state, duplicate hashes, and index version metadata. |
| Backend | FastAPI | Expose validated document, health, and chat endpoints to the UI. |
| Validation/config | Pydantic and pydantic-settings | Define request/response schemas and validate environment-based settings. |
| ASGI server | Uvicorn, one worker | Run the local FastAPI process and in-process ingestion worker. |
| Interface | Streamlit | Provide document controls, session chat, and source excerpts with minimal frontend setup. |
| HTTP client | HTTPX | Make bounded HTTP calls from UI/model adapters where direct HTTP is used. Reuse clients and set explicit timeouts. |
| Testing | pytest | Unit, API, and storage tests with temporary data and fake model clients. |
| Style checks | Ruff | Keep formatting and linting consistent through project configuration. |
| Version control | Git and GitHub | Track source, documentation, lockfile, and permitted small fixtures. |

Package integration details must be confirmed during setup. Avoid installing overlapping Ollama clients and adapter packages unless they have a defined responsibility. Keep model access behind application interfaces so retries, concurrency, and timeouts behave consistently.

## 3. Model strategy

The roadmap's starting generation choice is Qwen3 4B, with Nomic Embed Text for vectors. Download models explicitly; never trigger an unexpected network download from a chat request. Record model tags, digests, quantization where available, embedding dimension, tested context configuration, and license/terms links in the implementation's setup notes.

A model's parameter count is not its total memory requirement. Start with the technical design's conservative context and batch limits, serialize embedding and generation work, and measure actual resource use. Tags may change upstream; a reproducible setup needs recorded artifact identity. A changed embedding model or dimension requires reindexing. A smaller generation model is a possible future fallback only after evaluation; it is not a silently selected runtime alternative.

## 4. Dependency groups

The exact package names/versions are to be confirmed against official documentation during setup.

- Runtime: API/server, validation/configuration, multipart uploads, PDF parsing, RAG core and necessary adapters, vector storage, HTTP client, and Streamlit.
- Development: pytest, necessary API test support, and Ruff.
- System/local services: supported Python managed for the project, uv, Git, and Ollama.
- Model artifacts: generation and embedding downloads stored by the model runtime, never committed to Git.

Commit `pyproject.toml` and `uv.lock`. Do not invent version pins in planning documents. Record the tested Python version and use the lockfile to reproduce package installation. Test package/model integration on Apple Silicon before treating setup as complete.

## 5. Ownership boundaries

- FastAPI owns orchestration and all writes to application data.
- SQLite is authoritative for which documents exist and are ready.
- ChromaDB owns searchable chunk/vector records, not document readiness.
- LlamaIndex helps integrate RAG components; it must not bypass selected-document filtering or create hidden competing persistence.
- Ollama computes embeddings and generated answers; it does not manage document state.
- Streamlit handles presentation and session history; it accesses storage through API calls.
- The server maps validated model source IDs to filename/page metadata; the model cannot invent authoritative citations.

## 6. Configuration and data locations

Expose validated settings for the data directory, local API and Ollama URLs, model names, upload/page/text limits, chunking, retrieval/context limits, model timeout, queue capacity, and log level. Actual environment variable names will be defined in `.env.example` during setup and must match application configuration.

Keep PDFs under `data/uploads/`, vectors under `data/chroma/`, and metadata in `data/metadata.sqlite3`. Ignore the entire data directory, `.venv`, real `.env` files, model artifacts, caches, and content-bearing logs. Commit only safe configuration examples and synthetic/permitted fixtures. The roadmap PDF is a local planning reference and should not be copied into the repository by default.

## 7. What we are deferring

| Technology or feature | Reason to defer |
| --- | --- |
| PostgreSQL / pgvector | Embedded metadata/vector stores meet the single-user local scope. |
| Next.js / React | Streamlit covers the initial document-and-chat interface. |
| LangGraph / multi-agent frameworks | This project needs a controlled retrieval-and-answer pipeline. |
| Docker | Native setup comes first; containerization can follow a working MVP if needed. |
| Redis / Celery | One in-process worker is sufficient initially; restart recovery is explicit. |
| Cloud LLM APIs | The MVP requires local inference without paid API dependencies. |
| OCR packages | Scanned-document support is outside the initial product scope. |
| Ragas / Langfuse | Begin with a small inspectable evaluation set and local timing; add tooling when its benefit is clear. |
| Rerankers / hybrid search | Add after measured retrieval failures justify more components. |

## 8. Setup verification checklist

- [ ] Verify official package compatibility with the chosen Python and Apple Silicon environment.
- [ ] Review dependency/model licenses and record applicable distribution constraints.
- [ ] Lock dependencies and verify installation in a clean virtual environment.
- [ ] Confirm both local models are available and record identities.
- [ ] Confirm embeddings have a stable dimension and inputs are not silently truncated.
- [ ] Confirm configured context/output settings are supported and the complete prompt fits.
- [ ] Measure ingestion and generation memory with serialized calls.
- [ ] Confirm persistent stores survive restart and use the expected fingerprint.
- [ ] Verify runtime works with external network unavailable after setup.
- [ ] Record tested versions, startup commands, and limitations in README.

## 9. Change policy

Replace a selected technology only for a concrete compatibility, licensing, resource, or product reason. Record the reason and update the TDD, dependency lock, configuration, tests, and relevant implementation tasks together. Re-run affected quality checks; rebuild indexes if embedding or chunking identity changes. No stack component is considered installed merely because it appears here.
