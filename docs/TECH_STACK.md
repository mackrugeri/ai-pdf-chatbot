# Technology Stack: AI PDF Chatbot

Status: user-confirmed main stack, version 1.1
Date: 2026-11-13

## 1. Scope and selection principles

This document records the technologies we intend to use, their responsibilities, and what must be verified before installation. It is a design choice, not an installed dependency inventory or a compatibility certification. See [PRD.md](PRD.md) for scope, [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md) for contracts, and [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for delivery tasks.

Choose a local-first Python stack that can be learned incrementally on an Apple Silicon MacBook with 16 GB unified memory. Normal runtime must not need a paid API key or remote AI service. Keep one backend, one lightweight UI, a local PostgreSQL service for metadata, persistent ChromaDB vector storage, and bounded model concurrency.

## 2. Main stack

**Python, Ollama, Qwen3 4B, LlamaIndex, ChromaDB, FastAPI, Streamlit.**

These seven technologies are the user-confirmed main stack for implementation.

| Layer | Main technology | Responsibility |
| --- | --- | --- |
| Language | Python | Application, document processing, and service code. |
| Local model runtime | Ollama | Run the generation and embedding models locally. |
| Answer generation | Qwen3 4B | Generate answers grounded in retrieved PDF excerpts. |
| RAG framework | LlamaIndex | Coordinate document chunking, indexing, and retrieval through the selected integrations. |
| Vector database | ChromaDB | Persist and search chunk embeddings with source metadata. |
| Backend API | FastAPI | Expose document management, readiness, and question-answering endpoints. |
| User interface | Streamlit | Provide PDF uploads, document selection, chat, and source citations. |

### Supporting dependencies and tools

The following support the main stack. They are not additional primary frameworks or replacements for the seven technologies above.

| Supporting choice | Purpose |
| --- | --- |
| Python 3.11 initial target | Verify compatibility before locking the project Python version. |
| uv and `.venv` | Manage the environment and reproducible dependency lockfile. |
| Nomic Embed Text through Ollama | Generate local chunk/question embeddings; Qwen3 4B remains the answer model. |
| PyMuPDF | Extract page-level PDF text; verify licensing before distribution. |
| PostgreSQL with Psycopg 3 and a bounded connection pool | Track document lifecycle, hashes, and index configuration in a local database service. PostgreSQL is the user-selected metadata database. |
| Pydantic and pydantic-settings | Validate API schemas and configuration. |
| Uvicorn, one worker | Serve the FastAPI application locally. |
| HTTPX | Make local HTTP calls with explicit timeouts where needed. |
| pytest | Test processing, API behavior, and persistence. |
| Ruff | Format and lint Python code. |
| Git and GitHub | Track source, planning documents, and safe fixtures. |

Package integration details must be confirmed during setup. Avoid installing overlapping Ollama clients and adapter packages unless they have a defined responsibility. Keep model access behind application interfaces so retries, concurrency, and timeouts behave consistently.

## 3. Model strategy

The user-confirmed generation model is Qwen3 4B (`qwen3:4b` through Ollama); Nomic Embed Text is the supporting embedding model. Download models explicitly; never trigger an unexpected network download from a chat request. Record model tags, digests, quantization where available, embedding dimension, tested context configuration, and license/terms links in the implementation's setup notes.

A model's parameter count is not its total memory requirement. Start with the technical design's conservative context and batch limits, serialize embedding and generation work, and measure actual resource use. Tags may change upstream; a reproducible setup needs recorded artifact identity. A changed embedding model or dimension requires reindexing. A smaller generation model is a possible future fallback only after evaluation; it is not a silently selected runtime alternative.

## 4. Dependency groups

The exact package names/versions are to be confirmed against official documentation during setup.

- Runtime: API/server, validation/configuration, multipart uploads, PDF parsing, RAG core and necessary adapters, vector storage, Psycopg 3 with pooling support, HTTP client, and Streamlit.
- Development: pytest, necessary API test support, and Ruff.
- System/local services: supported Python managed for the project, uv, Git, Ollama, and PostgreSQL.
- Model artifacts: generation and embedding downloads stored by the model runtime, never committed to Git.

Commit `pyproject.toml` and `uv.lock`. Do not invent version pins in planning documents. Record the tested Python version and use the lockfile to reproduce package installation. Test package/model integration on Apple Silicon before treating setup as complete.

## 5. Ownership boundaries

- FastAPI owns orchestration and all writes to application data.
- PostgreSQL is authoritative for which documents exist and are ready.
- ChromaDB owns searchable chunk/vector records, not document readiness.
- LlamaIndex helps integrate RAG components; it must not bypass selected-document filtering or create hidden competing persistence.
- Ollama computes embeddings and generated answers; it does not manage document state.
- Streamlit handles presentation and session history; it accesses storage through API calls.
- The server maps validated model source IDs to filename/page metadata; the model cannot invent authoritative citations.

## 6. Configuration and data locations

Expose validated settings for `DATABASE_URL` (including database credentials), connection pool limits, the data directory, local API and Ollama URLs, model names, upload/page/text limits, chunking, retrieval/context limits, model timeout, queue capacity, and log level. Actual environment variable names will be defined in `.env.example` during setup and must match application configuration.

Keep PDFs under `data/uploads/` and vectors under `data/chroma/`. Store metadata in a dedicated local PostgreSQL database; its service-managed data directory stays outside the repository. Configure the connection through `DATABASE_URL`, provide only a placeholder in `.env.example`, and exclude database dumps/backups from Git. Ignore the entire data directory, `.venv`, real `.env` files, model artifacts, caches, and content-bearing logs. Commit only safe configuration examples and synthetic/permitted fixtures. The roadmap PDF is a local planning reference and should not be copied into the repository by default.

## 7. What we are deferring

| Technology or feature | Reason to defer |
| --- | --- |
| pgvector | PostgreSQL stores metadata; ChromaDB remains the selected vector database. |
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
- [ ] Install/start local PostgreSQL, create the application database and role, configure `DATABASE_URL`, and apply migrations.
- [ ] Verify database connection failures are handled and storage tests use an isolated test database.
- [ ] Confirm persistent stores survive restart and use the expected fingerprint.
- [ ] Verify runtime works with external network unavailable after setup.
- [ ] Record tested versions, startup commands, and limitations in README.

## 9. Change policy

Replace a selected technology only for a concrete compatibility, licensing, resource, or product reason. Record the reason and update the TDD, dependency lock, configuration, tests, and relevant implementation tasks together. Re-run affected quality checks; rebuild indexes if embedding or chunking identity changes. No stack component is considered installed merely because it appears here.
