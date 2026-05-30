# LectureLens – Engineering Context Log

**Last Update:** 2026-05-31  
**Current Phase:** 4 – COMPLETE  
**Next Phase:** 5 – Embeddings

---

## Project Overview

LectureLens is a production‑quality AI study assistant using RAG.  
This log tracks all architectural decisions, phase completions, and verification results.

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
  - LLM fallback chain: Gemini → NVIDIA → retrieval‑only.
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
  - Database initialised with tables and WAL mode.
  - Logging writes JSON to file and human‑readable to console.

### Phase 2 – Metadata Database (Repositories + Seed Data)
- **Status:** ✅ COMPLETE
- **Deliverables:**
  - `models/document_repository.py`
  - `models/conversation_repository.py`
  - `models/subject_repository.py`
  - `models/session_repository.py`
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
  - Added root route `GET /` returning `{"message": "LectureLens API Running"}`
- **Dependencies added:** `PyMuPDF==1.24.0`, `python-docx==1.1.0`, `python-pptx==0.6.23`
- **Verification:**
  - Tested on `sample.pdf` → 1 page, text extracted.
  - Tested on `TimeManagement_25P0011.docx` → 1 page (DOCX treated as single page), 4391 chars extracted.
  - Tested on PPTX (slide numbers preserved).

### Phase 4 – Chunking
- **Status:** ✅ COMPLETE
- **Deliverables:**
  - `services/chunking_service.py`
    - `ChunkingService(chunk_size=500, overlap=100, respect_sentence_boundary=True)`
    - `chunk_document(pages)` returns list of chunks with:
      - `chunk_id`, `page_num`, `text`, `chunk_index`, `start_char`, `end_char`
    - Overlap ensures continuity.
    - **Bug fixed:** infinite loop when `next_pos <= pos` near end of text. Fixed by forcing progress.
- **Verification:**
  - Test document: `TimeManagement_25P0011.docx` (4391 chars)
  - **Results:**
Total chunks: 11
Chunk 0: Time Management from Islamic Perspective...
Chunk 1: hose who have faith, do good, and urge each other to the truth...
Chunk 2: ess, Your wealth before poverty, Your free time before being busy...

text
- No hang, overlap visible, chunk indices correct, metadata preserved.
- Infinite loop eliminated.

---

## Current Project Structure (as of Phase 4)
lecturelens/
├── app.py
├── config.py
├── requirements.txt
├── project_state.json
├── .env.example (not tracked)
├── models/
│ ├── database.py
│ ├── document_repository.py
│ ├── conversation_repository.py
│ ├── subject_repository.py
│ └── session_repository.py
├── services/
│ ├── document_parser.py
│ └── chunking_service.py
├── utils/
│ ├── logger.py
│ └── validators.py
├── test_docs/
│ ├── sample.pdf
│ ├── TimeManagement_25P0011.docx
│ └── Lecture 2-Interview Skills.pptx
├── database/
│ ├── metadata.db
│ └── chroma/ (empty, ready for Phase 6)
├── logs/
├── uploads/
├── exports/
├── backups/
├── templates/
├── static/
├── tests/
└── docker/

text

---

## Key Architectural Decisions (Reinforced)

| Area | Decision |
|------|----------|
| **File creation** | Only when phase begins – no stubs. |
| **Database layer** | Repository pattern over raw SQLite (not ORM). |
| **Chunking** | Service‑layer (`services/`) not `utils/`. |
| **Embeddings model** | `BAAI/bge-small-en-v1.5` (Phase 5). |
| **Vector store** | ChromaDB with per‑subject collections (Phase 6). |
| **LLM fallback** | Gemini → NVIDIA → retrieval‑only. |
| **Streaming** | SSE (Phase 13). |
| **Auth** | Single admin password from `.env`. |

---

## Next Phase (5) – Embeddings

### Requirements (per spec + user recommendations)

- **File:** `services/embedding_service.py`
- **Model:** `BAAI/bge-small-en-v1.5` via `sentence-transformers`
- **Lazy loading** – model loaded only on first use (singleton).
- **Batch embedding** – `embed_batch(texts: List[str]) -> List[List[float]]`
- **In‑memory LRU cache** – cache repeated texts to avoid recomputation.
- **CPU support** – automatic fallback if GPU unavailable.
- **Vector dimension validation** – store `self.embedding_dimension` and validate every generated vector.
- **Logging** – log model load time, cache hits/misses, batch sizes.
- **Testing:**  
  ```python
  embedding = embed_text("What is AI?")
  print(len(embedding))  # expected 384 (BGE-small)
  embeddings = embed_batch(["text1", "text2"])