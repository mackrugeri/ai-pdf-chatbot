# Implementation Plan: AI PDF Chatbot

Status: planned work, version 1.0
Date: 2026-11-12

## 1. Inputs and working rules

Build against [PRD.md](PRD.md), [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md), and [TECH_STACK.md](TECH_STACK.md). This checklist records planned work, not completed implementation. Work in `/Users/Ahsan/Documents/Projects/ai-pdf-chatbot`. The target is 15 focused working days rather than fixed calendar dates.

Complete each milestone's exit checks before moving to dependent work. Update documents when an implementation decision changes their contracts. Keep uploads, model files, indexes, secrets, and private evaluation material out of commits. Use small implementation commits that represent working steps; the planning-document commits are separate from these future code commits.

## 2. Dependencies and critical path

```text
M1: project setup + extraction + chunking
 -> M2: metadata + model adapter + persistent ingestion
 -> M3: filtered retrieval + grounded answers
 -> M4: integrated API + UI
 -> M5: evaluation + reproducible release
```

Basic API scaffolding and storage interfaces begin early to support testing. Days 10–12 complete and integrate the API rather than introducing it for the first time.

## 3. Milestone 1: Foundation and PDF processing (Days 1–3)

### Day 1: Environment and application skeleton

- [ ] Verify Python/uv/Ollama availability and machine resources.
- [ ] Check official compatibility and licensing for selected packages/models; record decisions in TECH_STACK and lock compatible dependencies.
- [ ] Create `pyproject.toml`, `uv.lock`, `.gitignore`, `.env.example`, application configuration, and minimal README.
- [ ] Create FastAPI entry point and health schema with dependency injection.
- [ ] Create synthetic/permitted fixtures and a temporary-directory test harness.

Exit: clean setup launches the backend; configuration is validated; secrets and data paths are ignored. Covers NFR-02 and NFR-05.

### Day 2: Upload validation and page extraction

- [ ] Implement bounded upload streaming, generated filenames, SHA-256, and temporary-file cleanup.
- [ ] Verify readable PDF content and reject encrypted files, excessive page counts, and excessive text.
- [ ] Extract page text with original page indices and count textless pages.
- [ ] Return useful errors for malformed and entirely textless documents.

Exit: validation fixtures cover valid, damaged, encrypted, oversized, textless, and mixed-text PDFs. Covers FR-01 and FR-12.

### Day 3: Page-aware chunking

- [ ] Implement page-bounded, deterministic chunks with overlap and guaranteed forward progress.
- [ ] Preserve document ID, filename, chunk index, and page metadata.
- [ ] Test blank middle pages, short pages, long paragraphs, and Unicode content.
- [ ] Start a 20-question evaluation file with expected source pages.

Exit: chunks are nonempty, bounded, stable, and traceable to original PDF pages. Covers FR-07.

## 4. Milestone 2: Persistent ingestion (Days 4–6)

### Day 4: Metadata and local model adapter

- [ ] Implement SQLite schema/version handling and document repository.
- [ ] Define lifecycle transitions and unique-hash duplicate behavior.
- [ ] Download the planned models explicitly and record tested tags/digests and licenses.
- [ ] Implement Ollama readiness checks, embedding adapter, explicit timeout, and shared model semaphore.
- [ ] Verify embedding dimensions and input limits without silent truncation.

Exit: real local embedding smoke test passes; routine tests use fakes; unavailable-model errors are actionable. Covers FR-02, FR-03, and FR-10.

### Day 5: Chroma storage and indexing worker

- [ ] Implement persistent collection and fingerprint compatibility checks.
- [ ] Store deterministic chunk records through bounded embedding batches.
- [ ] Add one ingestion worker with bounded queue and publish readiness only after all chunks persist.
- [ ] Wire upload/list/detail endpoints and duplicate responses.

Exit: a ready document has the expected vector count and remains available after restart. Covers FR-02 through FR-04 and NFR-03.

### Day 6: Failure recovery and deletion

- [ ] Clean partial vectors after ingestion failures and reconcile interrupted records on startup.
- [ ] Implement deleting state, idempotent cleanup, and orphan reconciliation.
- [ ] Reject deletion of pending/processing records with a retryable busy response.
- [ ] Add visibility coordination so deletion and chat cannot race.
- [ ] Document the explicit index rebuild procedure.

Exit: interruption, duplicate race, cleanup failure, restart, and delete tests pass with temporary real stores. Covers FR-09 and NFR-04.

## 5. Milestone 3: Retrieval and answers (Days 7–9)

### Day 7: Filtered retrieval

- [ ] Validate selected IDs and require ready, compatible documents.
- [ ] Embed questions and retrieve only allowed document chunks.
- [ ] Verify returned metadata against selection and bound retrieved context.
- [ ] Test empty/unknown/non-ready selections and cross-document isolation.

Exit: evidence cannot leak from unselected or failed documents. Covers FR-05.

### Day 8: Grounded generation

- [ ] Implement full-prompt token budgeting and bounded output.
- [ ] Build explicit untrusted-source delimiters and grounding instructions.
- [ ] Implement structured output validation, inline source markers, and one repair attempt.
- [ ] Resolve source metadata server-side and return only valid cited excerpts.
- [ ] Add deterministic no-retrieval abstention and model timeout/error behavior.

Exit: fake-model tests reject invented citations and malformed answers; a real-model example returns checkable sources. Covers FR-06, FR-07, FR-10, and FR-11.

### Day 9: First quality pass

- [ ] Complete exactly 20 evaluation questions: 15 answerable and five unsupported.
- [ ] Cover paraphrases, multiple passages, contradictions, document selection, and misleading PDF instructions.
- [ ] Record expected/retrieved pages, grounding, citations, abstention, and timing.
- [ ] Tune chunking or retrieval only against recorded failures; rebuild indexes when the fingerprint changes.

Exit: an evaluation report identifies specific failures and fixes without representing similarity as confidence. Covers PRD quality targets.

## 6. Milestone 4: API and Streamlit experience (Days 10–12)

### Day 10: Complete API contracts

- [ ] Finalize all routes, validation schemas, status codes, common error envelope, and request IDs.
- [ ] Make health report storage health and separate embedding/generation readiness.
- [ ] Test API behavior with temporary stores and fake model clients.
- [ ] Verify bounded concurrency and consistent overload responses.

Exit: API contract matches the TDD, including asynchronous ingestion failures and duplicate uploads. Covers FR-01 through FR-10.

### Day 11: Upload and document management UI

- [ ] Build service status, upload, progress polling, textless-page notices, selection, and deletion controls.
- [ ] Prevent rerun-triggered duplicate submissions and disable invalid actions.
- [ ] Show useful errors and supported-format/size limitations.

Exit: a user can upload, observe readiness, select, and remove documents through the UI. Covers FR-01, FR-02, FR-05, FR-09, FR-10, and FR-12.

### Day 12: Chat and sources UI

- [ ] Add independent question submission and session history.
- [ ] Show safe answer text and expandable source filename/page/excerpt.
- [ ] Add clear-history behavior and remove affected history entries after deletion.
- [ ] Explain independent-question behavior and original PDF page indexing.

Exit: full upload-to-answer flow works; source text is safe to display; clearing history preserves documents. Covers FR-06 through FR-08 and FR-12.

## 7. Milestone 5: Release verification (Days 13–15)

### Day 13: Integration and robustness

- [ ] Run unit, API, and real local storage tests.
- [ ] Verify backend interruption during indexing and cleanup recovery.
- [ ] Exercise missing Ollama/model, timeout, malformed output, queue capacity, and deletion races.
- [ ] Check logs and repository contents for accidental document text, secrets, or local data.

Exit: deterministic checks pass and no critical filtering, deletion, or privacy defect remains.

### Day 14: Local evaluation and performance

- [ ] Run the fixed evaluation set with real models and record model/configuration identity.
- [ ] Meet the PRD target: at least 12/15 answerable successes, all 5/5 unsupported abstentions, and valid metadata for every displayed citation.
- [ ] Record retrieval and end-to-end latency, ingestion time, peak memory, and document sizes on the target Mac.
- [ ] Demonstrate prepared runtime with external network unavailable.
- [ ] Fix failures, rerun affected checks, and rerun the full fixed evaluation if retrieval/prompt/model settings change.

Exit: quality targets are measured and met; unsupported promises are absent from documentation. Covers NFR-01 and NFR-03.

### Day 15: Documentation and demonstration

- [ ] Finish README setup, model downloads, startup commands, configuration, troubleshooting, test commands, and limitations.
- [ ] Document architecture, restart recovery, deletion, index rebuilding, and license considerations.
- [ ] Verify setup from a clean virtual environment with locked dependencies.
- [ ] Create a short permitted-data demo showing upload, grounded answer, unsupported question, and deletion.
- [ ] Record final acceptance results and known limitations in an evaluation report.

Exit: PRD release checklist passes and the project owner can reproduce the demonstration.

## 8. Suggested implementation commit boundaries

1. Python project configuration and backend skeleton.
2. Validated PDF extraction and page-aware chunking.
3. SQLite document lifecycle and duplicate handling.
4. Ollama adapter and persistent vector ingestion.
5. Recovery and complete document deletion.
6. Selected-document retrieval.
7. Grounded generation and citation validation.
8. Complete API contracts and errors.
9. Streamlit document management.
10. Chat interface and source display.
11. Evaluation fixtures, robustness fixes, and release documentation.

Group meaningful tests with their implementation. Do not create placeholder modules or unrelated changes just to follow this list.

## 9. Risks and responses

| Risk | Response |
| --- | --- |
| Model exceeds practical memory budget | Serialize calls, reduce context/batches, measure; evaluate a smaller model only as a documented change. |
| Packages or model APIs differ from expectations | Verify official documentation during setup; lock tested versions and adapt the TDD. |
| Retrieval misses expected evidence | Inspect chunks and expected pages before changing the model; record tuning results. |
| Model follows instructions inside PDFs | Keep sources delimited and tool access absent; include adversarial cases and document residual limitations. |
| Storage operations partially fail | Keep lifecycle states authoritative, exclude incomplete records, and verify idempotent cleanup. |
| Work exceeds 15 days | Preserve MVP acceptance requirements; defer optional enhancements and revise the schedule. |

## 10. Definition of done

The product meets PRD acceptance criteria, code and tests are committed, fixed evaluation targets are met, local/offline operation is demonstrated, setup is reproducible, and known limitations are documented. Writing these planning files does not mean any implementation milestone is complete.
