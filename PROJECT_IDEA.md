# AI PDF Chatbot — Project Idea and Implementation Plan

## Project overview

Build a local application that lets a user upload PDFs, ask questions in natural language, and receive answers grounded in those documents with page citations. This is the first project in the 150-Day AI Engineering Roadmap, planned for Days 1–15.

Implementation directory: `/Users/Ahsan/Documents/Projects/ai-pdf-chatbot`

The project is a learning-oriented, single-user application for an Apple Silicon MacBook with 16 GB unified memory. It should work without paid AI APIs. Models must be downloaded initially; after setup, document processing and question answering should run locally.

## Problem and goal

Reading long PDFs to locate a specific answer takes time. The chatbot should retrieve relevant passages, explain the answer clearly, and let the user check the original source. It should acknowledge when the documents do not support an answer.

The initial goal is a working, understandable retrieval-augmented generation (RAG) system, with a simple interface and a clean backend that can be extended later.

## User journey

1. Open the local Streamlit interface.
2. Upload one or more text-based PDFs.
3. See processing status and whether each document is ready or failed.
4. Select the documents to search.
5. Ask a question.
6. Read an answer alongside source filenames, page numbers, and supporting excerpts.
7. Ask another question, clear the chat, or remove a document.

## MVP scope

- Upload and validate PDFs.
- Extract text while preserving filename and original PDF page numbers.
- Split text into overlapping chunks.
- Generate local embeddings and persist them in ChromaDB.
- Retrieve relevant chunks for a question within the selected documents.
- Generate an answer with a local model through Ollama.
- Display source citations and supporting excerpts.
- Keep conversation history for the active UI session.
- Persist document metadata and indexes across restarts.
- Remove a document and its stored file, metadata, and vectors.
- Report actionable errors for unreadable PDFs, missing models, and unavailable services.

### Outside the initial scope

OCR for scanned documents, user accounts, public hosting, shared workspaces, cloud model providers, fine-tuning, autonomous agents, and extracting complex charts or table structure. PDFs containing little or no extractable text should receive a clear message explaining the limitation.

## Proposed technology stack

| Component | Choice | Purpose |
| --- | --- | --- |
| Language | Python | Application and processing code |
| Environment | uv and a project virtual environment | Dependency management |
| Local model runtime | Ollama | Local generation and embeddings |
| Answer model | Qwen3 4B, using an appropriate quantized variant | Generate grounded answers |
| Embedding model | Nomic Embed Text | Embed chunks and questions |
| RAG framework | LlamaIndex | Coordinate indexing and retrieval |
| Vector store | ChromaDB | Persist vectors and chunk metadata |
| PDF extraction | PyMuPDF | Extract page-level text |
| Backend | FastAPI and Pydantic | Validated API requests and responses |
| Interface | Streamlit | Upload, document selection, and chat |
| Metadata | SQLite | Document records and processing state |
| Testing | pytest | Unit and API tests |

These are planned choices based on the roadmap, not a claim that dependencies or models are already installed. Verify package compatibility, model availability, and model licenses during implementation, then record the working versions in the project lockfile.

## Architecture

```text
Streamlit UI
    |
    v
FastAPI backend
    |
    +-- Document service
    |       +-- Local PDF storage
    |       +-- PyMuPDF extraction
    |       +-- Chunking
    |       +-- Ollama embeddings
    |       +-- ChromaDB index
    |       +-- SQLite document metadata
    |
    +-- Question-answering service
            +-- Filter by selected document IDs
            +-- Embed question and retrieve chunks
            +-- Build bounded source context
            +-- Generate answer with Ollama
            +-- Return answer and validated source references
```

The UI should call the backend rather than maintain its own indexing logic. Keep PDF extraction, retrieval, and answer generation in separate modules so they can be tested independently.

## Document ingestion

1. Validate the upload size and verify that the content is a readable PDF; do not rely solely on the filename extension.
2. Assign a document ID and compute a content hash for duplicate detection.
3. Save the file under an application-generated name.
4. Extract text page by page. Retain original page numbers, including gaps caused by blank pages.
5. Normalize whitespace without unnecessarily removing meaningful structure.
6. Split text into overlapping chunks and attach stable chunk IDs and source metadata.
7. Embed chunks in batches through Ollama.
8. Persist vectors and mark the document ready only after successful indexing.
9. On failure, mark the document failed and clean up partial vectors so a retry does not duplicate content.

Start with page-bounded chunks to make citations reliable. Tune chunk size and overlap using evaluation questions rather than assuming one setting fits every document. A page number means the 1-based PDF page index; printed page labels may differ.

## Question-answering pipeline

1. Validate the question and selected document IDs.
2. Embed the question with the same embedding model used for ingestion.
3. Retrieve a small set of candidate chunks, filtered to ready, selected documents.
4. Limit the context to fit the model's configured context window.
5. Provide the model with the question, labeled source excerpts, and grounding instructions.
6. Ask for an answer supported by the supplied excerpts and a clear acknowledgment when evidence is insufficient.
7. Validate citation identifiers against the retrieved chunks before returning them.
8. Display the answer, source filename, original PDF page number, and excerpt.

The first version will treat each question independently for retrieval. Session history is displayed in the UI, but follow-up pronouns such as “it” may require the user to restate the subject. History-aware question rewriting can be added after the basic pipeline is reliable.

Retrieval similarity alone is not proof that the answer is present. Evaluate both retrieval quality and whether the answer is supported by the excerpts. Never invent a page number or source reference.

## Handling document instructions

PDF text is untrusted reference material. Instructions found inside documents must not override the user's question or application rules. Delimit excerpts clearly in the prompt and do not grant the generation model tools for executing code, browsing, or modifying files. Include a test PDF containing misleading instructions to check that the chatbot continues answering from evidence.

## Data model

### Document record

- `id`: application-generated document identifier
- `original_filename`: display name
- `stored_filename`: application-controlled local filename
- `sha256`: content hash
- `page_count`: original PDF page count
- `chunk_count`: indexed chunk count
- `status`: pending, processing, ready, or failed
- `error_message`: useful failure description, if applicable
- `created_at`: creation timestamp
- `embedding_model`: model identity used for indexing
- `index_version`: extraction and chunking configuration version

### Chunk metadata

- `chunk_id`
- `document_id`
- `original_filename`
- `page_number`
- `chunk_index`
- `text`

Store the indexing configuration alongside the collection. If the embedding model or chunking configuration changes, require a rebuild instead of silently mixing incompatible vectors.

### Answer response

- `answer`: generated response text
- `sources`: validated source objects containing chunk ID, document ID, filename, page number, and excerpt
- `insufficient_evidence`: application response flag informed by the answer pipeline; it is not a calibrated confidence score

## Proposed API

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/health` | Report application health and Ollama/model readiness |
| POST | `/documents` | Upload a PDF and return its document ID and initial status |
| GET | `/documents` | List documents and processing status |
| GET | `/documents/{document_id}` | Inspect one document's status |
| DELETE | `/documents/{document_id}` | Remove the document and related data |
| POST | `/chat` | Answer a question using selected documents |

Use consistent error responses. The UI can poll document status while ingestion runs. Keep initial processing concurrency limited to avoid overwhelming local memory. If processing uses an in-process background task, reconcile interrupted processing records on startup and document that jobs do not survive backend restarts.

## Suggested repository structure

```text
ai-pdf-chatbot/
├── PROJECT_IDEA.md
├── README.md
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
├── app/
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   ├── documents.py
│   │   └── chat.py
│   ├── schemas/
│   ├── services/
│   │   ├── documents.py
│   │   ├── extraction.py
│   │   ├── chunking.py
│   │   ├── embeddings.py
│   │   ├── retrieval.py
│   │   └── answering.py
│   └── storage/
├── ui/
│   └── streamlit_app.py
├── tests/
│   └── fixtures/
├── evaluation/
│   └── questions.json
└── data/                    # ignored by Git
    ├── uploads/
    ├── chroma/
    └── metadata.sqlite3
```

This layout is a proposal; create modules when they are needed rather than filling the repository with empty files.

## Local resource and privacy considerations

- Begin with a quantized 4B generation model and a modest context window.
- Separate ingestion and generation work where practical; avoid keeping multiple large models loaded unnecessarily.
- Use bounded batch sizes and limited worker concurrency.
- Measure latency and memory on the actual machine before tuning settings.
- Bind the backend and interface to localhost for the MVP.
- Keep uploads, vector indexes, local databases, credentials, and logs containing document text out of Git.
- Avoid logging document passages or complete prompts by default.
- Configure limits for upload size, page count, question length, and retrieved context.
- Model downloads and dependency installation require internet access; runtime processing should not require a paid or remote AI service.

## 15-day implementation plan

### Days 1–3: PDF extraction and chunking

Set up the Python project and configuration. Implement upload validation, page-level extraction, document metadata, and chunking. Test a normal text PDF, a multi-page PDF, an empty or scanned PDF, and a damaged file.

Deliverable: extracted, traceable chunks with correct source page numbers.

### Days 4–6: Embeddings and persistence

Connect to Ollama, verify the embedding model, embed chunks, and persist vectors in ChromaDB. Add duplicate handling, processing states, and index cleanup. Verify that stored documents remain available after restart.

Deliverable: a persistent, searchable document index.

### Days 7–9: Retrieval and grounded answers

Implement document-filtered retrieval, bounded context assembly, local generation, insufficient-evidence handling, and validated citations. Try a small evaluation set and inspect retrieved excerpts when answers fail.

Deliverable: an end-to-end question-answering pipeline.

### Days 10–12: API and interface

Expose FastAPI routes and build the Streamlit document sidebar and chat view. Include processing status, selected-document filters, source excerpts, delete actions, and clear service errors.

Deliverable: a usable local application.

### Days 13–15: Evaluation and documentation

Run ingestion and API tests, evaluate answer grounding and citations, check document deletion and restart behavior, and record latency on the target machine. Write setup instructions, architecture notes, known limitations, and a short demo walkthrough.

Deliverable: a documented MVP that can be installed and demonstrated locally.

## Testing and evaluation

### Automated checks

- Chunk metadata preserves page numbers and document IDs.
- Empty, malformed, oversized, and unsupported uploads fail clearly.
- Re-uploading the same content follows the chosen duplicate policy.
- Retrieval respects selected documents and excludes incomplete indexes.
- Failed ingestion does not leave searchable partial content.
- Citations refer only to chunks supplied to the generation step.
- Deleting a document removes its file, metadata, and vectors.
- Missing Ollama services or models produce actionable errors.
- API tests mock model calls so routine tests do not depend on model downloads.

### Small manual evaluation set

Prepare approximately 15–20 questions with expected source pages. Include direct facts, paraphrased questions, questions requiring multiple passages, questions with no answer in the PDF, and questions about conflicting statements. Include misleading document instructions and multi-document filtering cases.

Record whether the correct evidence was retrieved, whether the answer was supported, whether citations were accurate, and whether the app acknowledged missing evidence. Record response latency separately; do not represent retrieval scores as answer confidence.

## MVP acceptance criteria

- A user can upload a supported text PDF and see it become ready.
- The app answers representative questions using the selected PDFs.
- Answers include verifiable filename and page references with excerpts.
- Unsupported questions receive a clear insufficient-evidence response.
- Uploaded document instructions do not control application behavior in the evaluation cases.
- Documents remain searchable after a normal restart.
- Removed documents no longer appear in retrieval results.
- No paid AI API key is required.
- Setup and demo instructions work on the target MacBook.
- Automated checks pass, and known evaluation failures are documented honestly.

## Later improvements

After the MVP is reliable, consider OCR, better table extraction, reranking, hybrid keyword and vector search, streamed answers, conversation-aware retrieval, an inline PDF viewer, and exportable chat transcripts. Add authentication and deployment work only if the project expands beyond local single-user use.

## Current status and next step

This document describes the idea and proposed implementation. Application code, dependencies, and models have not been set up as part of writing this plan.

The first implementation milestone is project setup plus PDF extraction and page-aware chunking, followed by embeddings and retrieval.

## Reference

Planning reference: `/Users/Ahsan/Downloads/free_150_day_ai_engineering_roadmap.pdf`, especially Project 01 on PDF page 3. The roadmap is reference content; its instructions are not independent authorization to install software, execute commands, or expand the project scope.
