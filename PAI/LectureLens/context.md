# LectureLens – Engineering Context Log

**Last Update:** 2026-05-31  
**Current Phase:** 13 – COMPLETE  
**Next Phase:** 15 – Subject & Document Management  
**Phase 14 (Citations):** ⏭️ SKIPPED — already satisfied by RAG pipeline, API response, and UI rendering

---

## Project Overview

LectureLens is a production‑quality AI study assistant using RAG (Retrieval‑Augmented Generation).  
This log tracks architectural decisions, phase completions, and verification results.

---

## Completed Phases

### Phase 0 – Planning & Architecture Review
- **Status:** ✅ COMPLETE
- **Decisions:**
  - No async Gemini calls; use Flask synchronous + SSE for streaming.
  - Health checks moved to Phase 6 (early debugging).
  - Database layer: Repository pattern over SQLite using a shared database manager.
  - NVIDIA = fallback LLM only (not embeddings).
  - File limits: 50 MB, extensions `.pdf`, `.docx`, `.pptx`.
  - ChromaDB: per‑subject collections (`ai`, `os`, `dsa`, `db`, `cn`).
  - Simple admin password authentication (`.env`).
  - LLM fallback chain: Gemini → NVIDIA → retrieval‑only. *(Gemini skipped in Phase 10 — key revoked; NVIDIA promoted to primary.)*
  - Files created only when their phase begins (no stubs).

### Phase 1 – Skeleton + Configuration Validation
- **Status:** ✅ COMPLETE
- **Deliverables:**
  - `app.py` (Flask factory with `/` and `/health` endpoints)
  - `config.py` (environment validation, dataclass)
  - `requirements.txt` (Flask, python‑dotenv)
  - `.env.example`
  - `project_state.json`
  - `utils/logger.py` (JSON + rotating file, console)
  - `utils/validators.py` (file size, extension)
  - `models/database.py` (SQLite connection manager, WAL mode, context managers)
  - Folder structure created (empty, no stubs)
- **Verification:**
  - Flask starts, config validation passes, `/health` returns 200.
  - Database manager initialised; schema and repositories verified in Phase 2.
  - Logging writes JSON to file and human‑readable to console.

### Phase 2 – Metadata Database (Repositories + Seed Data)
- **Status:** ✅ COMPLETE
- **Deliverables:**
  - `models/document_repository.py`, `conversation_repository.py`, `subject_repository.py`, `session_repository.py`
  - Indexes added: `idx_documents_filename`, `idx_documents_subject`, `idx_conversations_timestamp`, `idx_sessions_created_at`
  - Seed default subjects: `AI`, `Operating Systems`, `DSA`, `Databases`, `Computer Networks`
- **Verification:**
  - `app.py` loads all repositories.
  - Subjects seeded once (idempotent).
  - Indexes confirmed via `sqlite3 .indexes`.
  - No duplicate subjects on restart.

### Phase 3 – Document Parsing
- **Status:** ✅ COMPLETE
- **Deliverables:**
  - `services/document_parser.py`
    - Unified `parse_document(file_path)`
    - Supports PDF (PyMuPDF), DOCX (python‑docx), PPTX (python‑pptx)
    - Returns `{"metadata": {...}, "pages": [{"page_num": int, "text": str}, ...]}`
    - Graceful handling: encrypted PDF, corrupted/empty files, unsupported extensions
    - **DOCX pagination note:** DOCX files are treated as a single logical page (`page_num = 1`). No native page boundary exists in the `python-docx` API. Must be revisited before implementing citation references in later phases.
    - **PPTX pagination note:** PPTX files use slide index as the page reference (`page_num = slide_number`), 1‑based. This is the authoritative page reference for all future citation and retrieval logic involving PPTX documents.
  - Added root route `GET /` returning `{"message": "LectureLens API Running"}`
- **Dependencies added:** `PyMuPDF==1.24.0`, `python-docx==1.1.0`, `python-pptx==0.6.23`
- **Verification:**
  - Tested on `sample.pdf` → 1 page, text extracted.
  - Tested on `TimeManagement_25P0011.docx` → 1 logical page, 4391 chars extracted.
  - Tested on PPTX → slide numbers used as page references, preserved correctly.

### Phase 4 – Chunking
- **Status:** ✅ COMPLETE
- **Deliverables:**
  - `services/chunking_service.py`
    - `ChunkingService(chunk_size=500, overlap=100, respect_sentence_boundary=True)`
    - `chunk_document(pages)` returns list of chunks with `chunk_id`, `page_num`, `text`, `chunk_index`, `start_char`, `end_char`
    - Overlap ensures continuity across chunk boundaries.
    - **Bug fixed:** infinite loop when `next_pos <= pos` near end of text. Fixed by forcing `next_pos = end` when no progress is made.
- **Verification:**
  - **Large‑document validation completed:** 4391‑character DOCX → 11 chunks.
  - No hang, overlap visible, chunk indices correct, metadata preserved.

### Phase 5 – Embeddings
- **Status:** ✅ COMPLETE
- **Deliverables:**
  - `services/embedding_service.py`
    - Model: `BAAI/bge-small-en-v1.5` via `sentence-transformers`, name read from `config.py` (`EMBEDDING_MODEL_NAME`) — model swaps are a single config change.
    - Lazy loading – singleton initialised on first use.
    - `embed_text(text: str) -> List[float]` – LRU‑cached (maxsize 1024).
    - `embed_batch(texts: List[str]) -> List[List[float]]`
    - `embed_chunks(chunks: List[Dict]) -> List[Dict]` – appends `"embedding"` key to each chunk dict; canonical input for ChromaDB ingestion.
    - CPU fallback if GPU unavailable.
    - Vector dimension validation: `self.embedding_dimension = 384`; asserted on every return.
    - Logging: model name, load time, cache hits/misses, batch sizes.
    - **Fix:** Replaced deprecated `get_sentence_embedding_dimension()` with `get_embedding_dimension()`.
- **Verification:**
  ```
  embed_text("What is AI?")             → len 384  ✅
  embed_batch(["text1", "text2"])       → shape (2, 384)  ✅
  embed_chunks(chunks)                  → each dict has "embedding", len 384  ✅
  ```
  - `embeddings.position_ids UNEXPECTED` BertModel warning: confirmed benign — standard when loading BGE weights into a SentenceTransformer wrapper.

### Phase 6 – Vector Store (ChromaDB)
- **Status:** ✅ COMPLETE
- **Deliverables:**
  - `services/vector_store.py`
    - Persistent ChromaDB client; data stored under `database/chroma/`.
    - Collection naming: `lecturelens_<subject_slug>` (e.g. `lecturelens_operating_systems`).
    - `add_chunks(subject, chunks)` – inserts `embed_chunks()` output directly.
    - `search(subject, query_embedding, top_k) -> List[Dict]` – cosine similarity; returns `id`, `distance`, `text`, full metadata.
    - `delete_document(subject, document_id) -> int` – removes all chunks for a document; returns count.
    - `delete_subject_collection(subject)` – drops entire collection.
    - Embedding dimension validated on every insert.
    - **Bug fixed:** `_get_or_create_collection` caught only `ValueError`; ChromaDB raises `chromadb.errors.NotFoundError` (not a `ValueError` subclass). Fixed by importing and catching `NotFoundError` explicitly with `ValueError` retained for older-version fallback.
- **Verification:**
  ```
  add_chunks → Insertion successful  ✅
  search     → test_1: 0.1811, test_2: 0.2654 (correct cosine ordering)  ✅
  delete     → Deleted 2 chunks; subsequent search returns 0 results  ✅
  ```

### Phase 7 – Upload System (Background Indexing)
- **Status:** ✅ COMPLETE
- **Deliverables:**
  - `utils/hashing.py` – SHA256 file hashing for duplicate detection.
  - `task_queue/__init__.py` + `task_queue/indexing_queue.py` – background worker using `threading.Thread` + `queue.Queue` (single worker; Celery is overkill for portfolio scope).
  - `services/indexing_service.py` – full pipeline orchestration: `parse_document` → `chunk_document` → `embed_chunks` → `VectorStore.add_chunks` → `DocumentRepository` update.
  - `routes/upload_routes.py` – Flask blueprint; `POST /upload` returns `202` immediately with `document_id`; indexing proceeds in background.
  - `app.py` updated: blueprint registered, worker started on app startup.
- **Fixes applied during implementation:**
  - Renamed `queue/` → `task_queue/` to avoid shadowing the Python built‑in `queue` module.
  - Resolved Flask application context error by using module‑level logger and passing dependencies explicitly to the background thread.
  - Aligned `DocumentRepository.create()` signature to accept optional `document_id`; removed `upload_time` parameter (auto‑generated by DB).
- **Verification (live terminal output):**
  ```
  POST /upload  →  202, {"message": "Document upload accepted, indexing in background",
                         "original_filename": "TimeManagement_25P0011.docx",
                         "subject": "Operating Systems"}  ✅

  Background worker logs:
    Model loaded. Embedding dimension: 384
    ChromaDB client initialized at database/chroma
    Created new collection: lecturelens_operating_systems
    Added 11 chunks to collection 'lecturelens_operating_systems'
    Successfully indexed document <uuid> (TimeManagement_25P0011.docx)  ✅

  SQLite query:
    [('TimeManagement_25P0011.docx', 'Operating Systems', 'completed')]  ✅
  ```
  - Full parse → chunk → embed → vector store → DB pipeline verified end‑to‑end under real HTTP upload conditions.

---

## Current Project Structure (as of Phase 7 — superseded; see Phase 12 section)

```
lecturelens/
├── app.py
├── config.py
├── requirements.txt
├── project_state.json
├── .env.example (not tracked)
├── models/
│   ├── database.py
│   ├── document_repository.py
│   ├── conversation_repository.py
│   ├── subject_repository.py
│   └── session_repository.py
├── services/
│   ├── document_parser.py
│   ├── chunking_service.py
│   ├── embedding_service.py
│   ├── vector_store.py
│   └── indexing_service.py
├── routes/
│   └── upload_routes.py
├── task_queue/
│   ├── __init__.py
│   └── indexing_queue.py
├── utils/
│   ├── logger.py
│   ├── validators.py
│   └── hashing.py
├── test_docs/
│   ├── sample.pdf
│   ├── TimeManagement_25P0011.docx
│   └── Lecture 2-Interview Skills.pptx
├── database/
│   ├── metadata.db
│   └── chroma/  (populated – lecturelens_* collections)
├── logs/
├── uploads/
├── exports/
├── backups/
├── templates/
├── static/
├── tests/
└── docker/
```

---

## Completed Phases (continued)

### Phase 8 – Hybrid Search
- **Status:** ✅ COMPLETE
- **Deliverables:**
  - `services/search_service.py` – hybrid search orchestration.
    - `vector_search(subject, query, top_k)` – embeds query → ChromaDB cosine search.
    - `keyword_search(subject, query, top_k)` – SQLite FTS5 `MATCH` query against `chunks_fts`.
    - `hybrid_search(subject, query, top_k, alpha)` – weighted score fusion (`alpha` default `0.7`, favouring vector).
  - SQLite FTS5 virtual table `chunks_fts` (`chunk_id`, `text`); populated by `indexing_service.py` after ChromaDB insert.
  - `GET /search` endpoint in `routes/` – accepts `subject`, `query`, optional `top_k`, `alpha`.
- **Design decisions:**
  - Score fusion: linear weighted blend (RRF evaluated but weighted blend gave better tuning control).
  - Cosine distance inverted to similarity score before blending.
  - FTS5 populated in the same background job, after ChromaDB insert.
- **Verification:** Query `"time management"` against `Operating Systems` subject returned top 5 ranked chunks with blended scores and page references.

### Phase 9 – RAG Pipeline
- **Status:** ✅ COMPLETE
- **Deliverables:**
  - `services/rag_pipeline.py` – end‑to‑end RAG orchestration.
    - Calls `hybrid_search` → retrieves top‑k chunks → formats context with citations → passes to LLM → returns answer + source list.
  - Prompt template: instructs model to synthesise from provided context only; includes citation markers.
  - Retrieval‑only fallback: if LLM unavailable, returns ranked chunks as plain text.
- **Verification:** Pipeline retrieves relevant chunks and produces a structured prompt ready for LLM consumption.

### Phase 10 – Gemini Integration
- **Status:** ⏭️ SKIPPED
- **Reason:** Gemini API key revoked before implementation. NVIDIA promoted to primary LLM.
- **Impact on architecture:** LLM fallback chain revised from `Gemini → NVIDIA → retrieval‑only` to `NVIDIA → retrieval‑only`. `config.py` updated to make `GEMINI_API_KEY` optional (no validation error if absent).

### Phase 11 – NVIDIA Integration
- **Status:** ✅ COMPLETE
- **Deliverables:**
  - `services/llm_client.py` – NVIDIA client (replaces Gemini dependency).
    - Calls NVIDIA inference API with context + prompt.
    - Returns synthesised answer string.
    - Graceful fallback to retrieval‑only if API call fails.
  - `services/rag_pipeline.py` updated to route exclusively through NVIDIA client.
  - `config.py` updated: `GEMINI_API_KEY` marked optional; `NVIDIA_API_KEY` required.
- **Verification:**
  - NVIDIA API returns `200` — no `404` errors.
  - LLM synthesises answers across multiple chunks with natural language (not a raw chunk dump).
  - Citations accurately attributed to source pages.
  - Example query: *"Why do companies use stress interviews and how should a candidate respond?"* → answer synthesised from pages 5, 6, and 19 of `Lecture 2-Interview Skills.pptx`.
  - Fallback (retrieval‑only) intact but not triggered during testing.
  - **Observation (non‑blocking):** Prompt may encourage extractive quoting in some responses. Prompt engineering improvement deferred — not a pipeline defect.

---

## Current Project Structure (as of Phase 11)

```
lecturelens/
├── app.py
├── config.py
├── requirements.txt
├── project_state.json
├── .env.example (not tracked)
├── models/
│   ├── database.py
│   ├── document_repository.py
│   ├── conversation_repository.py
│   ├── subject_repository.py
│   └── session_repository.py
├── services/
│   ├── document_parser.py
│   ├── chunking_service.py
│   ├── embedding_service.py
│   ├── vector_store.py
│   ├── indexing_service.py
│   ├── search_service.py
│   ├── rag_pipeline.py
│   └── llm_client.py
├── routes/
│   ├── upload_routes.py
│   └── search_routes.py
├── task_queue/
│   ├── __init__.py
│   └── indexing_queue.py
├── utils/
│   ├── logger.py
│   ├── validators.py
│   └── hashing.py
├── test_docs/
│   ├── sample.pdf
│   ├── TimeManagement_25P0011.docx
│   └── Lecture 2-Interview Skills.pptx
├── database/
│   ├── metadata.db
│   └── chroma/  (populated – lecturelens_* collections)
├── logs/
├── uploads/
├── exports/
├── backups/
├── templates/
├── static/
├── tests/
└── docker/
```

---

## Key Architectural Decisions (Reinforced)

| Area | Decision |
|------|----------|
| **File creation** | Only when phase begins – no stubs. |
| **Database layer** | Repository pattern over raw SQLite (not ORM). |
| **Chunking** | Service‑layer (`services/`) not `utils/`. |
| **Embeddings model** | `BAAI/bge-small-en-v1.5` (384‑dim), pinned in `config.py` as `EMBEDDING_MODEL_NAME`. |
| **Vector store** | ChromaDB persistent client; per‑subject collections (`lecturelens_<subject_slug>`). |
| **ChromaDB error handling** | Catch `chromadb.errors.NotFoundError` (not `ValueError`) for missing collections. |
| **Chunk enrichment** | `embed_chunks()` output is the canonical format for ChromaDB ingestion. |
| **Hybrid search** | Linear weighted blend (alpha=0.7 vector, 0.3 FTS5); cosine distance inverted before blending. |
| **Background tasks** | `threading.Thread` + `queue.Queue` single worker — no Celery. |
| **Queue module naming** | `task_queue/` (not `queue/`) to avoid shadowing the Python built‑in. |
| **Upload response** | `202 Accepted` with `document_id`; status polled separately. |
| **Duplicate detection** | SHA256 hash before processing; reject or return existing ID if hash present in DB. |
| **Pipeline error handling** | Any step failure marks `document.status = "failed"` in SQLite and logs full traceback. |
| **LLM primary** | NVIDIA (Gemini skipped — key revoked). `GEMINI_API_KEY` optional in config. |
| **LLM fallback** | NVIDIA → retrieval‑only (Gemini removed from chain). |
| **Prompt engineering** | Extractive quoting tendency noted; prompt refinement deferred to a later polish phase. |
| **Streaming** | SSE (Phase 13). |
| **Auth** | Single admin password from `.env`. |

---

## Completed Phases (continued)

### Phase 12 – Chat Service
- **Status:** ✅ COMPLETE
- **Deliverables:**
  - `services/chat_service.py` – orchestrates a single chat turn: accepts `session_id`, `subject`, `user_message`; calls `rag_pipeline.answer()`; persists Q&A pair to `ConversationRepository`; returns `{"answer", "citations", "retrieved_chunks", "session_id"}`.
  - `routes/chat_routes.py` – Flask blueprint; `POST /chat` and `GET /chat/history` endpoints.
  - `models/fts_repository.py` – FTS5 virtual table `chunks_fts` initialised on startup (confirmed in logs).
- **Bugs diagnosed and fixed during implementation:**
  - **`lecturelens_general` NotFoundError (initial crash):** When `subject` was omitted, `routes/chat_routes.py` defaulted to `"General"`, which attempted to query a non-existent ChromaDB collection. **Fix 1:** `vector_store.search()` now catches `NotFoundError` and returns an empty list instead of crashing. **Fix 2:** Default subject changed from `"General"` to `None` in `chat_routes.py`.
  - **Cross-subject search (design gap):** When `subject is None`, the original code had no strategy for finding relevant chunks. **Fix:** Added `VectorStore.search_all()` — queries every `lecturelens_*` collection, merges results, sorts by cosine distance, returns top-k. `SearchService.hybrid_search()` routes to `search_all()` when subject is `None` or empty; FTS5 keyword search runs across all chunks regardless of subject (no scoping needed there).
  - **Duplicate-upload / Chroma reconstruction concern (investigated, no action needed):** Logs showed `"Duplicate document already exists"` blocking re-upload. Investigation confirmed ChromaDB collection `lecturelens_operating_systems` was intact with 52 vectors (`client.list_collections()` verified). The duplicate check was functioning correctly; Chroma data was never lost. Recovery tooling deferred.
- **ChromaDB health confirmed:**
  ```
  lecturelens_ai                0 vectors  (empty – no AI docs uploaded yet)
  lecturelens_operating_systems 52 vectors ✅
  ```
- **Verification (live terminal output):**
  ```
  # With subject:
  POST /chat {"question": "What is a stress interview?", "subject": "Operating Systems"}
  → answer with citations, vector_score ≈ 0.93  ✅

  # Without subject (cross-subject search):
  POST /chat {"question": "What is a stress interview?"}
  → same answer, same citations, same vector_scores  ✅

  # Session continuity:
  POST /chat {"session_id": "xxx", "question": "How should I respond?"}
  → {"session_id": "xxx", ...}  ✅

  # History retrieval:
  GET /chat/history?session_id=xxx
  → {"history": [{"question": "...", "answer": "...", "timestamp": "..."}]}  ✅
  ```
  - Conversation Q&A pairs persisted to SQLite; history endpoint returns correct records.
  - `POST /chat` returns `200` with no errors under all test cases.

---

## Current Project Structure (as of Phase 12)

```
lecturelens/
├── app.py
├── config.py
├── requirements.txt
├── project_state.json
├── .env.example (not tracked)
├── models/
│   ├── database.py
│   ├── document_repository.py
│   ├── conversation_repository.py
│   ├── subject_repository.py
│   ├── session_repository.py
│   └── fts_repository.py
├── services/
│   ├── document_parser.py
│   ├── chunking_service.py
│   ├── embedding_service.py
│   ├── vector_store.py
│   ├── indexing_service.py
│   ├── search_service.py
│   ├── rag_pipeline.py
│   ├── llm_client.py
│   └── chat_service.py
├── routes/
│   ├── upload_routes.py
│   ├── search_routes.py
│   └── chat_routes.py
├── task_queue/
│   ├── __init__.py
│   └── indexing_queue.py
├── utils/
│   ├── logger.py
│   ├── validators.py
│   └── hashing.py
├── test_docs/
│   ├── sample.pdf
│   ├── TimeManagement_25P0011.docx
│   └── Lecture 2-Interview Skills.pptx
├── database/
│   ├── metadata.db
│   └── chroma/  (lecturelens_operating_systems: 52 vectors)
├── templates/
├── static/
│   ├── css/
│   └── js/
├── logs/
├── uploads/
├── exports/
├── backups/
├── tests/
└── docker/
```

---

## Key Architectural Decisions (Reinforced)

| Area | Decision |
|------|----------|
| **File creation** | Only when phase begins – no stubs. |
| **Database layer** | Repository pattern over raw SQLite (not ORM). |
| **Chunking** | Service‑layer (`services/`) not `utils/`. |
| **Embeddings model** | `BAAI/bge-small-en-v1.5` (384‑dim), pinned in `config.py` as `EMBEDDING_MODEL_NAME`. |
| **Vector store** | ChromaDB persistent client; per‑subject collections (`lecturelens_<subject_slug>`). |
| **ChromaDB missing collection** | `search()` catches `NotFoundError` and returns `[]` — no crash. |
| **Cross-subject search** | `VectorStore.search_all()` queries all `lecturelens_*` collections when `subject is None`. |
| **Chat subject default** | `subject = data.get("subject") or None` — never defaults to `"General"`. |
| **Chunk enrichment** | `embed_chunks()` output is the canonical format for ChromaDB ingestion. |
| **Hybrid search** | Linear weighted blend (alpha=0.7 vector, 0.3 FTS5); cosine distance inverted before blending. |
| **Background tasks** | `threading.Thread` + `queue.Queue` single worker — no Celery. |
| **Queue module naming** | `task_queue/` (not `queue/`) to avoid shadowing the Python built‑in. |
| **Upload response** | `202 Accepted` with `document_id`; status polled separately. |
| **Duplicate detection** | SHA256 hash; reject duplicate uploads. Chroma reconstruction tooling deferred (not needed yet). |
| **Pipeline error handling** | Any step failure marks `document.status = "failed"` in SQLite and logs full traceback. |
| **LLM primary** | NVIDIA (Gemini skipped — key revoked). `GEMINI_API_KEY` optional in config. |
| **LLM fallback** | NVIDIA → retrieval‑only (Gemini removed from chain). |
| **Prompt engineering** | Extractive quoting tendency noted; refinement deferred to a later polish phase. |
| **Chat session** | `session_id` is client-generated UUID; server auto-creates session record on first message. |
| **Conversation history** | Stateless per turn in Phase 12 — multi-turn context injection into LLM prompt deferred. |
| **Streaming** | SSE (Phase 13). |
| **Auth** | Single admin password from `.env`. |

---

## Completed Phases (continued)

### Phase 13 – Chat UI
- **Status:** ✅ COMPLETE
- **Deliverables:**
  - `routes/subjects_routes.py` – new Flask blueprint; `GET /subjects` returns the seeded subject list. Used by the UI dropdown.
  - `templates/chat.html` – full single-page interface: sidebar with subject dropdown, suggestion chips on welcome screen, chat message list, auto-resizing textarea, animated typing indicator.
  - `static/css/style.css` – dark-themed, sidebar layout, gold accent colour, responsive.
  - `static/js/chat.js` – vanilla JS; calls `POST /chat`, `GET /chat/history`, manages `session_id` in `localStorage` so history survives page reload; renders citation tags below each answer.
  - `app.py` – two targeted edits: `GET /` now serves `render_template('chat.html')` instead of JSON; `subjects_bp` registered alongside existing blueprints.
- **Design decisions confirmed:**
  - Vanilla HTML/CSS/JS — no frontend framework; zero new dependencies.
  - Subject dropdown populated dynamically from `GET /subjects`.
  - `session_id` in `localStorage`; client-generated UUID, persisted across reloads.
  - Citations rendered inline as `filename, Page N` tags.
  - Standard `fetch()` used — SSE streaming deferred.
- **Verification:** UI loaded in browser, subject dropdown populated, questions answered with citations, New Chat resets session, history survives page reload.

### Phase 14 – Citations
- **Status:** ⏭️ SKIPPED
- **Reason:** All acceptance criteria already satisfied:
  - Citations generated by `rag_pipeline.py` from chunk metadata.
  - API returns `{"citations": [{"filename": str, "page": int}]}` in every `/chat` response.
  - UI renders citation tags below each assistant answer.
  - No missing citation functionality remains.

---

## Current Project Structure (as of Phase 13)

```
lecturelens/
├── app.py
├── config.py
├── requirements.txt
├── project_state.json
├── .env.example (not tracked)
├── models/
│   ├── database.py
│   ├── document_repository.py
│   ├── conversation_repository.py
│   ├── subject_repository.py
│   ├── session_repository.py
│   └── fts_repository.py
├── services/
│   ├── document_parser.py
│   ├── chunking_service.py
│   ├── embedding_service.py
│   ├── vector_store.py
│   ├── indexing_service.py
│   ├── search_service.py
│   ├── rag_pipeline.py
│   ├── llm_client.py
│   └── chat_service.py
├── routes/
│   ├── upload_routes.py
│   ├── search_routes.py
│   ├── chat_routes.py
│   └── subjects_routes.py
├── task_queue/
│   ├── __init__.py
│   └── indexing_queue.py
├── utils/
│   ├── logger.py
│   ├── validators.py
│   └── hashing.py
├── test_docs/
│   ├── sample.pdf
│   ├── TimeManagement_25P0011.docx
│   └── Lecture 2-Interview Skills.pptx
├── database/
│   ├── metadata.db
│   └── chroma/  (lecturelens_operating_systems: 52 vectors)
├── templates/
│   └── chat.html
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── chat.js
├── logs/
├── uploads/
├── exports/
├── backups/
├── tests/
└── docker/
```

---

## Key Architectural Decisions (Reinforced)

| Area | Decision |
|------|----------|
| **File creation** | Only when phase begins – no stubs. |
| **Database layer** | Repository pattern over raw SQLite (not ORM). |
| **Chunking** | Service‑layer (`services/`) not `utils/`. |
| **Embeddings model** | `BAAI/bge-small-en-v1.5` (384‑dim), pinned in `config.py` as `EMBEDDING_MODEL_NAME`. |
| **Vector store** | ChromaDB persistent client; per‑subject collections (`lecturelens_<subject_slug>`). |
| **ChromaDB missing collection** | `search()` catches `NotFoundError` and returns `[]` — no crash. |
| **Cross-subject search** | `VectorStore.search_all()` queries all `lecturelens_*` collections when `subject is None`. |
| **Chat subject default** | `subject = data.get("subject") or None` — never defaults to `"General"`. |
| **Chunk enrichment** | `embed_chunks()` output is the canonical format for ChromaDB ingestion. |
| **Hybrid search** | Linear weighted blend (alpha=0.7 vector, 0.3 FTS5); cosine distance inverted before blending. |
| **Background tasks** | `threading.Thread` + `queue.Queue` single worker — no Celery. |
| **Queue module naming** | `task_queue/` (not `queue/`) to avoid shadowing the Python built‑in. |
| **Upload response** | `202 Accepted` with `document_id`; status polled separately. |
| **Duplicate detection** | SHA256 hash; reject duplicate uploads. Chroma reconstruction tooling deferred (not needed yet). |
| **Pipeline error handling** | Any step failure marks `document.status = "failed"` in SQLite and logs full traceback. |
| **LLM primary** | NVIDIA (Gemini skipped — key revoked). `GEMINI_API_KEY` optional in config. |
| **LLM fallback** | NVIDIA → retrieval‑only (Gemini removed from chain). |
| **Prompt engineering** | Extractive quoting tendency noted; refinement deferred to a later polish phase. |
| **Chat session** | `session_id` is client-generated UUID; server auto-creates session record on first message. |
| **Conversation history** | Stateless per turn in Phase 12 — multi-turn context injection into LLM prompt deferred. |
| **Frontend stack** | Vanilla HTML/CSS/JS — no framework, no build step, zero new dependencies. |
| **Subject dropdown** | Populated dynamically from `GET /subjects`; subjects blueprint registered in `app.py`. |
| **Session persistence (UI)** | `session_id` in `localStorage`; survives page reload. |
| **Citations (UI)** | Rendered inline as `filename, Page N` tags; Phase 14 skipped — already satisfied. |
| **Streaming** | SSE deferred — UI uses standard `fetch()`. |
| **Auth** | Single admin password from `.env`. |

---

## Pre-Phase-15 Validation Required

Before building document management, the retrieval layer must be validated under multi-subject, multi-document conditions. All testing so far has been against a single collection (`lecturelens_operating_systems`).

**Required validation uploads:**
- An AI lecture document → subject: `AI`
- A DSA lecture document → subject: `DSA`
- A Databases lecture document → subject: `Databases`

**Required validation queries:**
- Subject-specific: `"What is a binary search tree?"` with `subject = "DSA"` → should retrieve only DSA chunks.
- Cross-subject: `"What is time complexity?"` with no subject → should search across all collections and return the best match.
- Empty subject: `"What is a stress interview?"` with `subject = "AI"` (no AI docs yet) → should return "no information" gracefully.
- Multi-turn: two consecutive questions in the same session → both stored in history.

If all pass, the retrieval layer is considered production-ready for the project scope and Phase 15 can begin.

---

## Next Phase (15) – Subject & Document Management

### Goal
Provide an admin view for managing uploaded documents and monitoring collection health, without modifying the retrieval or LLM layers.

### Deliverables

- **`routes/admin_routes.py`** – Flask blueprint with the following endpoints:
  - `GET /admin/documents` – list all documents (filename, subject, status, upload time, chunk count).
  - `GET /admin/documents/<document_id>` – detail view for one document.
  - `DELETE /admin/documents/<document_id>` – remove document from SQLite + ChromaDB + FTS5.
  - `POST /admin/documents/<document_id>/reindex` – force re-embedding and re-insertion into ChromaDB (bypasses duplicate hash check).
  - `GET /admin/subjects` – per-subject statistics: document count, total chunks, collection vector count.
  - `GET /admin/health` – ChromaDB collection list with vector counts; SQLite document counts by status.
- **`templates/admin.html`** – simple admin dashboard (document table, subject stats, health panel).
- **`static/js/admin.js`** – vanilla JS for admin UI interactions (delete confirmation, reindex trigger).

### Design Decisions

| Concern | Decision |
|---------|----------|
| **Auth** | Same single admin password from `.env`; admin routes require password header or query param. |
| **Delete cascade** | `DELETE /admin/documents/<id>` must remove from: (1) ChromaDB via `vector_store.delete_document()`, (2) FTS5 via `fts_repository.delete_document()`, (3) SQLite `documents` table. All three or none (transactional). |
| **Reindex bypass** | `reindex` endpoint deletes existing vectors first, then runs the full indexing pipeline. Does not check SHA256 hash. |
| **Collection health** | `VectorStore.get_subject_collections()` already returns collection names; extend to return counts. |
| **No new dependencies** | All management logic uses existing service and repository layers. |

### Dependencies
No new external libraries.

---

## Phase Status Summary

| Phase | Title | Status |
|-------|-------|--------|
| 0 | Planning & Architecture Review | ✅ COMPLETE |
| 1 | Skeleton + Configuration Validation | ✅ COMPLETE |
| 2 | Metadata Database (Repositories + Seed Data) | ✅ COMPLETE |
| 3 | Document Parsing | ✅ COMPLETE |
| 4 | Chunking | ✅ COMPLETE |
| 5 | Embeddings | ✅ COMPLETE |
| 6 | Vector Store (ChromaDB) | ✅ COMPLETE |
| 7 | Upload System (Background Indexing) | ✅ COMPLETE |
| 8 | Hybrid Search | ✅ COMPLETE |
| 9 | RAG Pipeline | ✅ COMPLETE |
| 10 | Gemini Integration | ⏭️ SKIPPED (key revoked) |
| 11 | NVIDIA Integration | ✅ COMPLETE |
| 12 | Chat Service | ✅ COMPLETE |
| 13 | Chat UI | ✅ COMPLETE |
| 14 | Citations | ⏭️ SKIPPED (already satisfied) |
| 15 | Subject & Document Management | 🔄 READY (pending validation) |
| 16–29 | (Remaining phases) | ⏳ PENDING |

> **Assessment:** The full MVP stack is complete and UI-verified — upload, parse, chunk, embed, hybrid search, RAG, chat, citations, and web UI all work end‑to‑end.  
> The immediate prerequisite before Phase 15 is multi-subject retrieval validation. Once that passes, the retrieval layer is production-ready for the project scope.

**APPROVED – CONTINUE (Phase 15, pending validation)**