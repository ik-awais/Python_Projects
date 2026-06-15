<!-- LectureLens | AI-Powered Study Assistant | RAG Pipeline | Hybrid Search | Flask | ChromaDB | NVIDIA LLaMA 3.3 70B | Muhammad Awais | FAST-NUCES Peshawar | ik-awais.github.io -->

<!-- CAPSULE RENDER ANIMATED HEADER -->
<img src="https://capsule-render.vercel.app/api?type=venom&color=0:03001e,35:0b1a30,65:0a2a4a,100:0e4f8f&height=220&section=header&text=LectureLens&fontSize=64&fontColor=00c8ff&fontAlignY=45&desc=AI-Powered%20Study%20Assistant%20%7C%20RAG%20%7C%20Hybrid%20Search&descSize=17&descAlignY=68&descColor=5bc8ff&animation=fadeIn&stroke=0e4f8f&strokeWidth=1" width="100%"/>

<div align="center">

<img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" width="100%"/>

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=500&size=15&duration=2800&pause=900&color=00c8ff&center=true&vCenter=true&width=780&height=36&lines=Upload+your+lectures+%E2%80%94+Chat+with+them+instantly;RAG+%7C+Hybrid+Search+%7C+Page-Level+Citations;Flask+%7C+ChromaDB+%7C+NVIDIA+LLaMA+3.3+70B;Production-Grade+AI+Study+Assistant" alt="Tagline" />

<br/>

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20Store-FF6B35?style=for-the-badge&logo=databricks&logoColor=white)](https://www.trychroma.com)
[![NVIDIA](https://img.shields.io/badge/NVIDIA-LLaMA%203.3%2070B-76B900?style=for-the-badge&logo=nvidia&logoColor=white)](https://build.nvidia.com)
[![SQLite](https://img.shields.io/badge/SQLite-FTS5%20%7C%20WAL-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.2-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org)

<br/>

[![GitHub](https://img.shields.io/badge/Source-GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/ik-awais/Python_Projects/tree/main/PAI/LectureLens)
[![Portfolio](https://img.shields.io/badge/Portfolio-ik--awais.github.io-03001e?style=for-the-badge&logo=githubpages&logoColor=00c8ff)](https://ik-awais.github.io)
[![Author](https://img.shields.io/badge/Author-Muhammad%20Awais-9d6fff?style=for-the-badge&logo=person&logoColor=white)](https://www.linkedin.com/in/muhammad-awais-ai-engineer/)

<br/>

![RAG](https://img.shields.io/badge/RAG-Retrieval--Augmented%20Generation-0e4f8f?style=flat-square)
![Hybrid Search](https://img.shields.io/badge/Hybrid%20Search-Vector%20%2B%20FTS5-00c8ff?style=flat-square)
![Phase](https://img.shields.io/badge/Phase-13%20Complete%20%7C%20MVP%20Ready-22c55e?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-5bc8ff?style=flat-square)

> *"Upload your lecture slides and notes — then chat with them."*  
> LectureLens turns static academic documents into an interactive, citation-aware study assistant powered by a large language model.

<img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" width="100%"/>

</div>

---

## 📖 What Is LectureLens?

LectureLens is a **full-stack Retrieval-Augmented Generation (RAG)** application built for students and researchers. Instead of keyword-searching through PDFs or scrubbing through lecture slides, you upload your course material once and ask questions in plain English — receiving precise, grounded answers backed by **page-level citations** from your own documents.

The system is built on a production-quality Flask backend with non-blocking background indexing, a **ChromaDB vector store** organised by academic subject, a **SQLite FTS5 full-text search engine** for keyword recall, and **NVIDIA's hosted LLaMA 3.3 70B Instruct** as the reasoning layer. Every answer is grounded in your uploaded material — the LLM is explicitly instructed to say *"I don't have enough information"* rather than hallucinate.

<div align="center">
<img src="https://capsule-render.vercel.app/api?type=rect&color=0:03001e,100:0b1a30&height=3&section=header&animation=fadeIn" width="100%"/>
</div>

---

## ✨ Key Features

<div align="center">

| Feature | Description |
|:--------|:------------|
| 📄 **Multi-Format Ingestion** | PDF (PyMuPDF), DOCX (python-docx), PPTX (python-pptx) → unified page-level structure |
| 🔍 **Hybrid Search** | Dense vector similarity (70%) fused with SQLite FTS5 keyword search (30%) — higher recall than either alone |
| 🗂️ **Per-Subject Collections** | Each subject gets its own ChromaDB HNSW collection; cross-subject search works when no subject is specified |
| 📎 **Page-Level Citations** | Every answer includes `{filename, page}` pairs — students verify sources instantly |
| ⚡ **Non-Blocking Indexing** | Uploads return `202 Accepted` immediately; `ThreadPoolExecutor` handles the full pipeline asynchronously |
| 👁️ **Auto-Ingestion Watcher** | Daemon thread scans `uploads/<subject>/` on a configurable interval and auto-queues new files |
| 🔒 **SHA-256 Duplicate Detection** | File hash computed before any expensive parsing — identical documents rejected gracefully |
| 💬 **Session-Aware Chat History** | Q&A pairs persisted in SQLite under a UUID session ID; history survives page reloads |
| 🗑️ **Transactional Deletes** | Document removal cascades ChromaDB → FTS5 → SQLite atomically; any failure halts the chain |
| 🛡️ **Admin Dashboard** | Password-protected `/admin` panel — document listing, subject stats, vector counts, reindex triggers, live health monitoring |
| 🚀 **Lazy-Loaded Embeddings** | `BAAI/bge-small-en-v1.5` (384-dim, 33M params) loaded once on first use, LRU-cached per string |
| 🌐 **Zero-Dependency Frontend** | Vanilla HTML/CSS/JS — no framework, no build step; dark-themed UI with citation rendering |

</div>

<div align="center">
<img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" width="100%"/>
</div>

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Flask Application (app.py)                    │
│                  Application Factory Pattern                     │
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐ │
│  │ POST /upload │   │ POST /chat   │   │ /admin/*             │ │
│  │ upload_bp    │   │ chat_bp      │   │ admin_bp             │ │
│  └──────┬───────┘   └──────┬───────┘   └──────────────────────┘ │
│         │                  │                                     │
│         ▼                  ▼                                     │
│  ┌──────────────┐   ┌──────────────────────────────────────┐    │
│  │ Indexing     │   │           RAG Pipeline                │    │
│  │ Queue        │   │                                       │    │
│  │ (Thread      │   │  1. hybrid_search(question, subject)  │    │
│  │  Pool,       │   │  2. _build_context(chunks)            │    │
│  │  4 workers)  │   │  3. NVIDIAClient.generate(prompt)     │    │
│  └──────┬───────┘   │  4. _extract_citations(chunks)        │    │
│         │           └──────────────┬───────────────────────┘    │
│         ▼                          │                             │
│  ┌──────────────┐          ┌───────▼──────────────────────┐     │
│  │ Indexing     │          │      Search Service           │     │
│  │ Service      │          │                               │     │
│  │              │          │  vector_results (ChromaDB)    │     │
│  │ 1. SHA-256   │          │    score = 1/(1+distance)     │     │
│  │ 2. parse()   │          │  × 0.7 weight                 │     │
│  │ 3. chunk()   │          │                               │     │
│  │ 4. FTS insert│          │  keyword_results (FTS5)       │     │
│  │ 5. embed()   │          │    score = 1/(1+rank)         │     │
│  │ 6. chroma    │          │  × 0.3 weight                 │     │
│  │    .add()    │          │                               │     │
│  │ 7. status=ok │          │  merged by chunk_id, top-k    │     │
│  └──────┬───────┘          └───────┬──────────────────────┘     │
└─────────┼──────────────────────────┼────────────────────────────┘
          │                          │
   ┌──────▼──────────┐    ┌──────────▼──────────────────┐
   │  ChromaDB       │    │  SQLite (WAL mode)           │
   │  Vector Store   │◄───│                              │
   │                 │    │  documents  (status, hash)   │
   │  lecturelens_   │    │  conversations (session Q&A) │
   │  <subject>      │    │  sessions   (UUID → created) │
   │  (HNSW cosine)  │    │  subjects   (name registry)  │
   └────────┬────────┘    │  chunks_fts (FTS5 virtual)   │
            │             └──────────────────────────────┘
   ┌────────▼────────────────────┐
   │  NVIDIA API                 │
   │  meta/llama-3.3-70b-instruct│
   │  temperature=0.2            │
   │  max_tokens=500             │
   └─────────────────────────────┘
```

<div align="center">
<img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" width="100%"/>
</div>

---

## ⚙️ How It Works — Step by Step

### Step 1 — Upload & Validation

`POST /upload` receives a file and a subject label, validates the extension (`pdf`, `docx`, `pptx`) and size, saves with a `{uuid4_hex}_{secure_filename}` to prevent path traversal, enqueues an indexing task, and returns **`202 Accepted`** immediately — the caller is never blocked.

### Step 2 — Background Indexing Pipeline

The `IndexingQueue` (`ThreadPoolExecutor`, default 4 workers) runs the full `IndexingService.index_document()` pipeline:

| Step | Action |
|:-----|:-------|
| 1 | Compute SHA-256 hash → reject if duplicate already in DB |
| 2 | Parse: PDF page-by-page (PyMuPDF) · DOCX paragraphs as one page · PPTX slide-by-slide |
| 3 | Create SQLite record with `status='processing'` and a fresh UUID as `document_id` |
| 4 | Chunk with `ChunkingService` (500-char window, 100-char overlap, sentence-boundary snapping ±200 chars) |
| 5 | Insert raw chunk text into FTS5 virtual table `chunks_fts` |
| 6 | Batch-embed all chunks with `BAAI/bge-small-en-v1.5` → 384-dimensional float vectors |
| 7 | Enrich each chunk dict with `document_id` and `filename` metadata |
| 8 | Store in the subject's ChromaDB collection (created on demand, `hnsw:space=cosine`) |
| 9 | Update SQLite status to `'completed'`; on any exception → `'failed'` and re-raise |

### Step 3 — Hybrid Search

When `POST /chat` receives a question, `SearchService.hybrid_search()` runs two parallel searches and fuses their scores:

```
vector_score   = 1.0 / (1.0 + cosine_distance)   →  weight: 0.7
keyword_score  = 1.0 / (1.0 + fts5_rank)          →  weight: 0.3

combined_score = 0.7 × vector_score + 0.3 × keyword_score
```

Results are merged by `chunk_id`. Chunks appearing in only one leg receive a zero score for the other. Top-k by combined score become the retrieval context.

### Step 4 — RAG Answer Generation

`RAGPipeline.answer()` takes the retrieved chunks and:

1. Builds a context string with `[Source: {filename}, Page {page_num}]` headers above each chunk
2. Constructs a grounding system prompt: *"Use only the provided context. Say 'I don't have enough information' if the answer isn't there."*
3. Calls `NVIDIAClient.generate()` → `meta/llama-3.3-70b-instruct` at `temperature=0.2`
4. Extracts a deduplicated `[{filename, page}, ...]` citation list
5. Returns `{answer, citations, retrieved_chunks}` as JSON

### Step 5 — Chat History & Sessions

The first chat call creates a session UUID via `SessionRepository`. Every Q&A pair is stored in the `conversations` table. `GET /chat/history?session_id=<uuid>` returns the last 50 exchanges.

<div align="center">
<img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" width="100%"/>
</div>

---

## 🛠️ Tech Stack

<div align="center">

| Layer | Technology | Role |
|:------|:-----------|:-----|
| **Web Framework** | Flask 3.0 | REST API, blueprint routing, app factory |
| **LLM** | NVIDIA API — LLaMA 3.3 70B Instruct | Answer generation, `temperature=0.2` |
| **Embeddings** | `BAAI/bge-small-en-v1.5` (sentence-transformers) | 384-dim dense vectors, LRU-cached |
| **Vector Store** | ChromaDB 0.4 (persistent, HNSW cosine) | Semantic similarity retrieval |
| **Keyword Search** | SQLite FTS5 virtual table | Exact / partial keyword recall |
| **Relational DB** | SQLite with WAL mode | Documents, sessions, conversations, subjects |
| **PDF Parsing** | PyMuPDF (`fitz`) | Page-level text extraction |
| **DOCX Parsing** | `python-docx` | Paragraph-level text extraction |
| **PPTX Parsing** | `python-pptx` | Slide-level text extraction |
| **Background Jobs** | `concurrent.futures.ThreadPoolExecutor` | Non-blocking indexing |
| **Config** | `python-dotenv` + frozen `@dataclass` | Validated env-var config at startup |
| **Deep Learning** | PyTorch 2.2 (CPU) | Embedding model runtime |

</div>

<div align="center">

<br/>

<a href="https://skillicons.dev"><img src="https://skillicons.dev/icons?i=python,pytorch,flask,sqlite&theme=dark" /></a>
&nbsp;&nbsp;
<a href="https://skillicons.dev"><img src="https://skillicons.dev/icons?i=docker,linux,git,aws&theme=dark" /></a>

</div>

<div align="center">
<img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" width="100%"/>
</div>

---

## 📁 Project Structure

```
LectureLens/
│
├── app.py                          # Flask application factory
├── config.py                       # Frozen dataclass — validates all env vars at startup
├── requirements.txt                # Pinned production dependencies
│
├── routes/
│   ├── upload_routes.py            # POST /upload → validate, save, enqueue
│   ├── chat_routes.py              # POST /chat, GET /chat/history
│   ├── search_routes.py            # Search-only endpoint (no LLM)
│   ├── subjects_routes.py          # Subject CRUD
│   └── admin_routes.py             # /admin/* — stats, docs, health, reindex, delete
│
├── services/
│   ├── indexing_service.py         # Full pipeline orchestrator (parse→chunk→embed→store)
│   ├── document_parser.py          # Unified PDF / DOCX / PPTX parser
│   ├── chunking_service.py         # Sentence-boundary-aware sliding-window chunker
│   ├── embedding_service.py        # BAAI/bge-small-en-v1.5 — lazy load & LRU cache
│   ├── vector_store.py             # ChromaDB wrapper — per-subject collections, HNSW cosine
│   ├── search_service.py           # Hybrid search — weighted vector + FTS5 merge
│   ├── rag_pipeline.py             # Retrieve → prompt → NVIDIA LLM → citations
│   ├── chat_service.py             # Chat turn orchestration + session persistence
│   └── llm_client.py              # NVIDIA API client — LLaMA 3.3 70B Instruct
│
├── models/
│   ├── database.py                 # SQLite singleton — WAL mode, context-manager connections
│   ├── document_repository.py      # CRUD for documents table
│   ├── fts_repository.py           # FTS5 virtual table — insert, keyword_search, delete
│   ├── conversation_repository.py  # Q&A history per session
│   ├── session_repository.py       # Session UUID management
│   └── subject_repository.py       # Subject registry with default seeding
│
├── task_queue/
│   ├── indexing_queue.py           # ThreadPoolExecutor-backed global queue
│   └── folder_watcher.py           # Daemon thread — auto-ingests files dropped in uploads/
│
├── utils/
│   ├── hashing.py                  # SHA-256 streaming hash for duplicate detection
│   ├── validators.py               # Extension and size guards
│   └── logger.py                   # Structured rotating file + console logging
│
├── templates/
│   └── chat.html                   # Single-page chat interface
│
├── static/
│   ├── css/style.css               # Dark theme, sidebar layout, citation styling
│   └── js/chat.js                  # Vanilla JS — fetch, localStorage session, citation render
│
├── database/
│   ├── metadata.db                 # SQLite — documents, sessions, conversations, subjects, FTS5
│   └── chroma/                     # ChromaDB persistent collections (lecturelens_<subject>)
│
├── uploads/                        # Temporary file landing zone
├── logs/                           # Rotating structured logs
├── exports/
├── backups/
└── tests/
```

<div align="center">
<img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" width="100%"/>
</div>

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- An [NVIDIA API Key](https://build.nvidia.com) (for LLaMA 3.3 70B Instruct)
- Git

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/ik-awais/Python_Projects.git
cd Python_Projects/PAI/LectureLens

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env — set NVIDIA_API_KEY, FLASK_SECRET_KEY, ADMIN_PASSWORD

# 5. Run the application
python app.py
```

The API will be available at `http://localhost:5000`  
The Chat UI will be available at `http://localhost:5000`  
The Admin Dashboard will be available at `http://localhost:5000/admin`

<div align="center">
<img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" width="100%"/>
</div>

---

## ⚙️ Configuration Reference

All settings come from a `.env` file and are validated inside the frozen `Config.from_env()` classmethod at startup — missing required keys raise `ValueError` before the app even binds to a port.

| Variable | Default | Purpose |
|:---------|:--------|:--------|
| `NVIDIA_API_KEY` | **Required** | NVIDIA hosted inference auth |
| `FLASK_SECRET_KEY` | **Required** | Flask session signing |
| `ADMIN_PASSWORD` | **Required** | Protects all `/admin/*` routes |
| `GEMINI_API_KEY` | `None` | Optional fallback LLM |
| `CHROMA_PATH` | `./database/chroma` | ChromaDB persistent storage |
| `DATABASE_PATH` | `./database/metadata.db` | SQLite file path |
| `UPLOAD_FOLDER` | `./uploads` | Temporary file landing zone |
| `CHUNK_SIZE` | `500` | Characters per chunk |
| `OVERLAP` | `100` | Character overlap between chunks |
| `BATCH_SIZE` | `32` | Embedding batch size |
| `INDEXING_WORKERS` | `4` | Thread pool size |
| `MAX_FILE_SIZE_MB` | `2048` | Upload size guard |
| `WATCH_FOLDER_ENABLED` | `True` | Enable auto-ingestion watcher |
| `WATCH_FOLDER_INTERVAL_SECONDS` | `30` | Watcher scan interval |

<div align="center">
<img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" width="100%"/>
</div>

---

## 📡 API Reference

### Upload a Document
```http
POST /upload
Content-Type: multipart/form-data

file=<binary>
subject=<string>   # e.g. "Machine Learning"
```
Returns `202 Accepted` immediately; indexing runs in the background.
```json
{
  "message": "Document upload accepted, indexing in background",
  "original_filename": "week3_lecture.pdf",
  "subject": "Machine Learning"
}
```

### Chat (RAG)
```http
POST /chat
Content-Type: application/json

{
  "question": "What is gradient descent?",
  "subject": "Machine Learning",
  "top_k": 5,
  "session_id": "<optional-uuid>"
}
```
```json
{
  "answer": "Gradient descent is an optimisation algorithm that iteratively adjusts model parameters in the direction of steepest loss reduction...",
  "citations": [
    { "filename": "week3_lecture.pdf", "page": 12 },
    { "filename": "week3_lecture.pdf", "page": 14 }
  ],
  "session_id": "a1b2c3d4-...",
  "retrieved_chunks": [...]
}
```

### Chat History
```http
GET /chat/history?session_id=<uuid>
```
Returns last 50 Q&A pairs for the session.

### Admin — System Stats
```http
GET /admin/stats
X-Admin-Password: <password>
```
```json
{
  "total_documents": 42,
  "total_subjects": 6,
  "total_vectors": 18340,
  "completed_documents": 40,
  "failed_documents": 1,
  "pending_documents": 1
}
```

### Admin — Delete Document (Transactional)
```http
DELETE /admin/documents/<document_id>
X-Admin-Password: <password>
```
Cascades: ChromaDB vectors → FTS5 entries → SQLite row. Any failure stops the cascade and returns `500`.

### Admin — System Health
```http
GET /admin/health
X-Admin-Password: <password>
```
Returns queue worker status, ChromaDB health, and SQLite connectivity.

<div align="center">
<img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" width="100%"/>
</div>

---

## 🧠 Design Decisions & Engineering Notes

**Why hybrid search instead of pure vector search?**  
Vector similarity excels at semantic matching ("gradient descent" ↔ "optimisation algorithm") but can miss exact keyword hits like formula names, acronyms, or proper nouns. FTS5 catches these exactly. The 70/30 weighted merge gives the best of both: semantic breadth plus lexical precision.

**Why per-subject ChromaDB collections?**  
Namespacing by subject means a query about "neural networks" inside the Machine Learning collection won't surface irrelevant chunks from a History or Law collection. It also makes deletion transactional per-subject — dropping a subject clears its entire ChromaDB collection in one call.

**Why SQLite FTS5 rather than Elasticsearch?**  
Zero additional infrastructure. Python ships with `sqlite3`; FTS5 is built in. WAL mode handles concurrent Flask workers without table-level locking. The entire database is a single portable file.

**Why non-blocking upload with `ThreadPoolExecutor`?**  
Embedding a 200-slide PPTX through a transformer model can take 20–60 seconds. Blocking the HTTP response that long would break mobile clients and timeout proxies. The `202 Accepted` pattern keeps the API responsive regardless of document size.

**Why `BAAI/bge-small-en-v1.5`?**  
At 33M parameters it produces 384-dimensional embeddings that run fast on CPU and score well on MTEB retrieval benchmarks. Academic texts — dense with technical vocabulary — benefit from its BERT-style pretraining, and the small model size means the embedding step is never the bottleneck.

**Why a frozen `Config` dataclass?**  
An immutable config object loaded once at startup prevents accidental mutation across request handlers. `from_env()` validates every required key before `create_app()` returns, so misconfiguration fails loudly at boot rather than silently mid-request.

<div align="center">
<img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" width="100%"/>
</div>

---

## 📊 Development Phase Tracker

<div align="center">

| Phase | Title | Status |
|:-----:|:------|:------:|
| 0 | Planning & Architecture Review | ✅ Complete |
| 1 | Skeleton + Configuration Validation | ✅ Complete |
| 2 | Metadata Database (Repositories + Seed Data) | ✅ Complete |
| 3 | Document Parsing | ✅ Complete |
| 4 | Chunking | ✅ Complete |
| 5 | Embeddings | ✅ Complete |
| 6 | Vector Store (ChromaDB) | ✅ Complete |
| 7 | Upload System (Background Indexing) | ✅ Complete |
| 8 | Hybrid Search | ✅ Complete |
| 9 | RAG Pipeline | ✅ Complete |
| 10 | Gemini Integration | ⏭️ Skipped (key revoked) |
| 11 | NVIDIA Integration | ✅ Complete |
| 12 | Chat Service | ✅ Complete |
| 13 | Chat UI | ✅ Complete |
| 14 | Citations | ⏭️ Skipped (already satisfied by pipeline) |
| 15 | Subject & Document Management | 🔄 Ready (pending validation) |
| 16–29 | Remaining Phases | ⏳ Pending |

</div>

> **MVP Status:** The full MVP stack is complete and UI-verified — upload, parse, chunk, embed, hybrid search, RAG, chat, citations, and web UI all work end-to-end.

<div align="center">
<img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" width="100%"/>
</div>

---

## 💡 What I Learned

Building LectureLens end-to-end sharpened skills across the full production AI stack:

- **RAG pipeline design** — retrieval quality is the ceiling on answer quality; iterated on chunk size, overlap, and vector/keyword weight ratio to improve both precision and recall
- **Hybrid search implementation** — designing and calibrating score normalisation (`1/(1+x)`) so vector distances and FTS5 `rank` values are comparable before weighting
- **Concurrent document processing in Flask** — safely passing database repositories and vector store references into background threads without leaking Flask's request context
- **ChromaDB collection management** — HNSW index configuration, lazy client initialisation, and implementing transactional cascade deletes across a multi-store architecture
- **Production Flask patterns** — application factory, blueprint separation, dependency injection via `app.config`, and graceful shutdown via `atexit.register`
- **Operational observability** — building a health endpoint that reports queue worker status, ChromaDB availability, and SQLite connectivity in a single call

<div align="center">
<img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" width="100%"/>
</div>

---

## 👨‍💻 About the Author

<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=500&size=14&duration=3000&pause=1000&color=00c8ff&center=true&vCenter=true&width=720&height=30&lines=Muhammad+Awais+%7C+AI+Engineer+%7C+Managing+Director+%40+AI+GenMat;BS+Artificial+Intelligence+%E2%80%94+FAST-NUCES+Peshawar+(2025%E2%80%932029)" alt="Author" />

<br/>

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0a66c2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/muhammad-awais-ai-engineer/)
[![Portfolio](https://img.shields.io/badge/Portfolio-03001e?style=for-the-badge&logo=githubpages&logoColor=00c8ff)](https://ik-awais.github.io)
[![Upwork](https://img.shields.io/badge/Upwork-6FDA44?style=for-the-badge&logo=upwork&logoColor=white)](https://www.upwork.com/freelancers/~018a2d0e2f88ac4838)
[![Gmail](https://img.shields.io/badge/Gmail-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:mawaisqq@gmail.com)

</div>

---

## 🔗 Explore More Projects

### 🏥 [MediScan AI — Medical Image & Report Assistant](https://ik-awais.github.io/projects/mediscan-ai/)

An end-to-end medical imaging pipeline. A fine-tuned Vision Transformer classifies chest X-rays with confidence scores, IsolationForest scores anomalies against a distribution of "normal" embeddings, and LLaMA 3.1 70B generates structured radiology reports with FINDINGS, IMPRESSION, and RECOMMENDATION sections — all served through a single FastAPI endpoint.

`PyTorch` · `HuggingFace` · `FastAPI` · `OpenCV` · `LLaMA 3.1`

---

### 📄 [Document Q&A System](https://ik-awais.github.io/projects/document-qa-system/)

A production-ready RAG system for uploading PDF, DOCX, and TXT documents and asking natural-language questions. Answers include source citations. Built with LangChain, FAISS vector store, and a Streamlit interface for zero-config use.

`LangChain` · `FAISS` · `Streamlit` · `Python` · `LLM`

---

<div align="center">

*View all projects → [ik-awais.github.io](https://ik-awais.github.io)*

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=400&size=13&duration=3500&pause=1500&color=5bc8ff&center=true&vCenter=true&width=720&height=28&lines=ik-awais.github.io+%7C+m.awais%40aigenmat.com+%7C+mawaisqq%40gmail.com" alt="Contact" />

</div>

<!-- CAPSULE RENDER ANIMATED FOOTER -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:4a0e8f,50:0b0630,100:03001e&height=130&section=footer&text=Building%20the%20Future%20with%20AI&fontSize=20&fontColor=00c8ff&fontAlignY=65&animation=fadeIn" width="100%"/>