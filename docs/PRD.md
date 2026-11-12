# Product Requirements Document: AI PDF Chatbot

Status: implementation baseline, version 1.0
Date: 2026-11-12
Audience: project owner, developer, and tester

## 1. Purpose

Build a single-user local application that answers natural-language questions about uploaded text-based PDFs. Answers must include verifiable source excerpts and original PDF page numbers. The application should reduce time spent searching documents while making answers easy to check.

This document defines product behavior and acceptance criteria. [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md) defines implementation decisions, [TECH_STACK.md](TECH_STACK.md) defines technology choices, and [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) sequences delivery. The existing [PROJECT_IDEA.md](PROJECT_IDEA.md) provides background; these four documents are the implementation baseline. Changes to scope must update the affected requirements and tasks together.

The metadata database is local PostgreSQL; ChromaDB remains responsible for vector storage. Database setup and credentials must be documented without committing secrets.

## 2. Target user and environment

The primary user is a learner or developer who wants to question study material, manuals, and similar documents privately on an Apple Silicon MacBook with 16 GB unified memory. The initial interface and API are accessible only on localhost. Internet access is needed for dependency and model downloads; normal document processing must use local services and require no paid AI API key.

## 3. Goals and success measures

- Upload a supported PDF, index it, and ask questions through one interface.
- Return answers grounded in selected documents, with checkable citations.
- Clearly acknowledge missing evidence and unsupported files.
- Preserve indexed documents across restarts and fully remove deleted documents.
- Demonstrate a maintainable RAG application with repeatable setup and evaluation.

Release requires all deterministic acceptance checks below to pass. A fixed 20-question manual evaluation must achieve at least 12 of 15 answerable questions with correct supporting evidence and grounded answers, and all five unanswerable questions must acknowledge insufficient evidence. Every displayed citation must resolve to a supplied excerpt with a valid filename and PDF page. These are project release targets, not measured results or a general accuracy claim. Record all failures and latency on the target machine.

## 4. User journey

1. Open the UI and check service readiness.
2. Upload PDFs and observe queued, processing, ready, or failed states.
3. Select one or more ready documents.
4. Ask a self-contained question.
5. Read the answer and expand its source excerpts.
6. Ask more questions or clear the session history.
7. Delete an unwanted document and confirm that it disappears from future searches.

## 5. Functional requirements

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| FR-01 | Accept text-based PDFs within configured limits. | Valid PDF proceeds; malformed, encrypted/password-protected, oversized, over-page-limit, and textless files receive actionable errors. |
| FR-02 | Track processing state. | Every accepted upload has an ID and a visible state; failed documents show a useful error and are not searchable. |
| FR-03 | Detect byte-identical uploads. | A duplicate returns the existing document and does not create another index. Failed duplicates instruct the user to delete and upload again. |
| FR-04 | Persist documents. | Ready documents remain listed and searchable after a normal backend restart. |
| FR-05 | Restrict retrieval to selection. | Only selected ready document IDs contribute evidence; empty, unknown, or non-ready selections are rejected clearly. |
| FR-06 | Answer from retrieved evidence. | Supported questions produce grounded answers; missing evidence produces an explicit insufficient-evidence response. |
| FR-07 | Provide source citations. | Each substantive supported answer includes filename, 1-based original PDF page index, and source excerpt. Printed page labels may differ. |
| FR-08 | Display session history. | Questions, answers, and sources remain visible during the active UI session and can be cleared. |
| FR-09 | Delete documents. | Successful deletion removes stored PDF, metadata, and vectors; subsequent questions cannot retrieve them. Failed cleanup stays excluded and can be retried. |
| FR-10 | Report service failures. | Missing models, unavailable Ollama, timeouts, and incompatible indexes produce actionable messages rather than fabricated answers. |
| FR-11 | Treat document instructions as data. | Evaluation cases containing misleading PDF instructions do not cause instruction-following or unrelated answers. The model has no action tools. |
| FR-12 | Explain limitations in the UI. | UI states that OCR is unavailable, citations use PDF page indices, and each question must include its own context. |

## 6. Product boundaries

MVP includes multiple uploaded documents, local embeddings and generation, document selection, session-only chat history, and persistent document indexing. It does not include OCR, reliable reconstruction of complex tables/charts, semantic duplicate detection, persistent chat history, history-aware question rewriting, streaming, accounts, remote hosting, cloud models, fine-tuning, or autonomous agents.

Scanned or blank PDFs without extractable text fail clearly. Mixed PDFs may be accepted when some pages contain text, but the UI must report how many pages had no extractable text. English text is the initial evaluation scope. Cross-document contradictions should be attributed to their sources when retrieved; the system cannot promise exhaustive comparison of every page.

## 7. Nonfunctional requirements

| ID | Requirement | Verification |
| --- | --- | --- |
| NFR-01 | Runtime processing is local and requires no paid API. | Run the prepared application with external network unavailable and local Ollama running. |
| NFR-02 | Protect local document content. | Bind services to localhost; exclude uploads, indexes, databases, secrets, and content-bearing logs from Git; do not log passages by default. |
| NFR-03 | Bound resource use. | Enforce upload, page, text, question, context, and concurrency limits; record peak memory and latency on the target Mac. |
| NFR-04 | Recover from interruption. | Restart during ingestion leaves no incomplete document searchable; stale processing is marked failed. |
| NFR-05 | Make setup reproducible. | README setup works from a clean environment using locked dependencies and recorded model identities. |
| NFR-06 | Keep errors understandable. | Display user-facing error codes/messages without exposing local paths or stack traces. |

No latency service-level promise is made before benchmarking. The UI must remain able to show status while work is running.

## 8. Acceptance scenarios

- Upload a fixture containing blank pages between text pages; citations retain the original page positions.
- Upload the same bytes under a different filename; only one document is indexed.
- Ask about document B while only A is selected; B supplies no excerpts.
- Ask an unsupported question; no invented fact or citation is returned.
- Stop the backend during indexing and restart; partial vectors remain unavailable and are cleaned up.
- Delete a document, restart, and search again; its content remains absent.
- Shut down Ollama; the UI shows a service error and preserves existing document records.
- Clear chat history; document records remain intact.

## 9. Evaluation and release

Use synthetic or permitted public PDF fixtures, without private source content in the repository. The 20-question set contains 15 answerable cases covering direct facts, paraphrases, multi-passage answers, document filtering, contradictions, and misleading instructions, plus five unsupported cases. Record expected pages, retrieved pages, answer support, citation validity, abstention, and latency. Human review checks semantic support; identifier validation alone cannot establish factual correctness.

Release checklist: automated checks pass; evaluation targets are met; critical privacy/filtering/deletion failures are resolved; setup and offline runtime are demonstrated; limitations and remaining quality failures are documented.

## 10. Assumptions and changes

The project owner is the initial developer and acceptance reviewer. The schedule targets 15 focused working days and may change based on learning needs or hardware measurements. Defaults and implementation details are recorded in the technical design. Model and dependency compatibility must be verified during setup. Any future deployment beyond localhost requires a separate design for authentication and access control.
