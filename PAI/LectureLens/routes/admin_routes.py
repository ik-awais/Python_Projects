"""Admin blueprint – document management and system health endpoints.

Phase 15 deliverable. All delete operations are transactional:
ChromaDB → FTS5 → SQLite. Any failure aborts the remaining steps
and returns a 500 with a descriptive error.
"""

import logging
from functools import wraps
from flask import Blueprint, current_app, jsonify, request, render_template

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ── Auth decorator ────────────────────────────────────────────────────────────

def require_admin(f):
    """Validate X-Admin-Password header against config.ADMIN_PASSWORD."""
    @wraps(f)
    def decorated(*args, **kwargs):
        config = current_app.config.get('APP_CONFIG')
        admin_password = getattr(config, 'ADMIN_PASSWORD', None)
        if not admin_password:
            # No password configured – allow access (dev/test mode)
            return f(*args, **kwargs)
        provided = request.headers.get('X-Admin-Password', '')
        if provided != admin_password:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


# ── Page route ────────────────────────────────────────────────────────────────

@admin_bp.route('/', methods=['GET'])
def admin_page():
    """Serve the admin dashboard HTML."""
    return render_template('admin.html')


# ── Statistics ────────────────────────────────────────────────────────────────

@admin_bp.route('/stats', methods=['GET'])
@require_admin
def get_stats():
    """Aggregate overview statistics."""
    try:
        doc_repo     = current_app.config['DOCUMENT_REPO']
        subject_repo = current_app.config['SUBJECT_REPO']
        vector_store = current_app.config['VECTOR_STORE']

        all_docs  = doc_repo.get_all()
        subjects  = subject_repo.get_all()

        total_vectors = 0
        try:
            collections = vector_store.client.list_collections()
            for col in collections:
                try:
                    total_vectors += col.count()
                except Exception:
                    pass
        except Exception as e:
            logger.warning("Could not count vectors: %s", e)

        status_counts = {}
        for doc in all_docs:
            s = (doc.get('status') or 'unknown').lower()
            status_counts[s] = status_counts.get(s, 0) + 1

        return jsonify({
            'total_documents':    len(all_docs),
            'total_subjects':     len(subjects),
            'total_vectors':      total_vectors,
            'completed_documents': status_counts.get('completed', 0),
            'failed_documents':   status_counts.get('failed', 0),
            'pending_documents':  status_counts.get('pending', 0) + status_counts.get('indexing', 0),
        }), 200

    except Exception as e:
        logger.exception("Error in /admin/stats")
        return jsonify({'error': str(e)}), 500


# ── Health ────────────────────────────────────────────────────────────────────

@admin_bp.route('/health', methods=['GET'])
def health():
    queue = current_app.config.get('INDEXING_QUEUE')
    if queue is None:
        queue_status = {
            "status": "uninitialized",
            "workers": 0,
            "active_futures": 0,
            "pending_tasks": 0
        }
    else:
        stats = queue.get_stats()
        queue_status = {
            "status": "healthy" if queue.is_healthy() else "unhealthy",
            "workers": stats["workers"],
            "active_futures": stats["active_futures"],
            "pending_tasks": stats["pending_tasks"],
            "total_submitted": stats["total_submitted"],
            "shutdown": stats["shutdown"]
        }

    chroma_healthy = bool(current_app.config.get('VECTOR_STORE'))
    db_healthy = bool(current_app.config.get('DB_MANAGER'))

    # Flat fields for legacy frontend compatibility
    flat = {
        "queue_workers": queue_status["workers"],
        "queue_active": queue_status["active_futures"],
        "queue_pending": queue_status["pending_tasks"],
        "queue_status": queue_status["status"],
        "chroma_status": "healthy" if chroma_healthy else "unhealthy",
        "db_status": "healthy" if db_healthy else "unhealthy",
    }

    return jsonify({
        "indexing_queue": queue_status,
        "chromadb": "healthy" if chroma_healthy else "unhealthy",
        "database": "healthy" if db_healthy else "unhealthy",
        "status": "healthy" if queue_status["status"] == "healthy" and chroma_healthy and db_healthy else "degraded",
        **flat   # add flat fields at top level
    })


# ── Subjects analytics ────────────────────────────────────────────────────────

@admin_bp.route('/subjects', methods=['GET'])
@require_admin
def get_subjects():
    """Per-subject document count, chunk count, and vector count."""
    try:
        doc_repo     = current_app.config['DOCUMENT_REPO']
        subject_repo = current_app.config['SUBJECT_REPO']
        vector_store = current_app.config['VECTOR_STORE']
        db_manager   = current_app.config['DB_MANAGER']

        subjects = subject_repo.get_all()
        all_docs = doc_repo.get_all()

        # Group documents by subject name
        doc_by_subject = {}
        for doc in all_docs:
            s = doc.get('subject') or 'Unknown'
            doc_by_subject.setdefault(s, []).append(doc)

        # Chunk counts from FTS (fast – no embedding needed)
        chunk_by_subject = {}
        try:
            with db_manager.get_connection() as conn:
                rows = conn.execute(
                    "SELECT subject, COUNT(*) as cnt FROM documents "
                    "JOIN chunks ON documents.document_id = chunks.document_id "
                    "GROUP BY subject"
                ).fetchall()
                for row in rows:
                    chunk_by_subject[row[0]] = row[1]
        except Exception:
            # chunks table may not exist yet; silently ignore
            pass

        # Vector counts per collection
        vector_by_subject = {}
        try:
            collections = vector_store.client.list_collections()
            for col in collections:
                if not col.name.startswith('lecturelens_'):
                    continue
                slug    = col.name[len('lecturelens_'):]
                subject = slug.replace('_', ' ').title()
                try:
                    vector_by_subject[subject] = col.count()
                except Exception:
                    vector_by_subject[subject] = 0
        except Exception as e:
            logger.warning("Could not retrieve vector counts: %s", e)

        result = []
        for subj in subjects:
            name  = subj.get('name') or subj.get('subject') or str(subj)
            docs  = doc_by_subject.get(name, [])
            # Try exact match then case-insensitive
            vcount = vector_by_subject.get(name)
            if vcount is None:
                for k, v in vector_by_subject.items():
                    if k.lower() == name.lower():
                        vcount = v
                        break
            result.append({
                'name':           name,
                'document_count': len(docs),
                'chunk_count':    chunk_by_subject.get(name, 0),
                'vector_count':   vcount or 0,
            })

        return jsonify({'subjects': result}), 200

    except Exception as e:
        logger.exception("Error in /admin/subjects")
        return jsonify({'error': str(e)}), 500


# ── Documents list ────────────────────────────────────────────────────────────

@admin_bp.route('/documents', methods=['GET'])
@require_admin
def list_documents():
    """List all documents with metadata."""
    try:
        doc_repo = current_app.config['DOCUMENT_REPO']
        docs     = doc_repo.get_all()
        return jsonify({'documents': docs, 'total': len(docs)}), 200
    except Exception as e:
        logger.exception("Error in GET /admin/documents")
        return jsonify({'error': str(e)}), 500


# ── Document detail ───────────────────────────────────────────────────────────

@admin_bp.route('/documents/<document_id>', methods=['GET'])
@require_admin
def get_document(document_id):
    """Return full metadata for a single document."""
    try:
        doc_repo = current_app.config['DOCUMENT_REPO']
        doc = doc_repo.get_by_id(document_id)
        if not doc:
            return jsonify({'error': 'Document not found'}), 404
        return jsonify(doc), 200
    except Exception as e:
        logger.exception("Error in GET /admin/documents/%s", document_id)
        return jsonify({'error': str(e)}), 500


# ── Delete document ───────────────────────────────────────────────────────────

@admin_bp.route('/documents/<document_id>', methods=['DELETE'])
@require_admin
def delete_document(document_id):
    """
    Cascade delete: ChromaDB → FTS5 → SQLite.
    All three must succeed. Partial failures are logged and returned as 500.
    """
    try:
        doc_repo     = current_app.config['DOCUMENT_REPO']
        vector_store = current_app.config['VECTOR_STORE']
        db_manager   = current_app.config['DB_MANAGER']

        doc = doc_repo.get_by_id(document_id)
        if not doc:
            return jsonify({'error': 'Document not found'}), 404

        subject = doc.get('subject')

        # Step 1 – ChromaDB
        chroma_deleted = 0
        try:
            chroma_deleted = vector_store.delete_document(subject, document_id)
            logger.info("Deleted %d vectors for document %s from ChromaDB", chroma_deleted, document_id)
        except Exception as e:
            logger.error("ChromaDB delete failed for %s: %s", document_id, e)
            return jsonify({'error': f'ChromaDB delete failed: {e}'}), 500

        # Step 2 – FTS5
        try:
            from models.fts_repository import FTSRepository
            fts_repo = FTSRepository(db_manager)
            fts_repo.delete_document(document_id)
            logger.info("Deleted FTS entries for document %s", document_id)
        except Exception as e:
            logger.error("FTS delete failed for %s: %s", document_id, e)
            return jsonify({'error': f'FTS delete failed: {e}'}), 500

        # Step 3 – SQLite
        try:
            doc_repo.delete(document_id)
            logger.info("Deleted document %s from SQLite", document_id)
        except Exception as e:
            logger.error("SQLite delete failed for %s: %s", document_id, e)
            return jsonify({'error': f'SQLite delete failed: {e}'}), 500

        return jsonify({
            'message':       'Document deleted',
            'document_id':   document_id,
            'vectors_removed': chroma_deleted,
        }), 200

    except Exception as e:
        logger.exception("Unexpected error deleting document %s", document_id)
        return jsonify({'error': str(e)}), 500


# ── Reindex document ──────────────────────────────────────────────────────────

@admin_bp.route('/documents/<document_id>/reindex', methods=['POST'])
@require_admin
def reindex_document(document_id):
    """
    Force re-embedding of a document.
    1. Delete existing vectors from ChromaDB.
    2. Reset status to 'pending'.
    3. Enqueue indexing job (bypasses SHA256 duplicate check).
    """
    try:
        doc_repo     = current_app.config['DOCUMENT_REPO']
        vector_store = current_app.config['VECTOR_STORE']

        doc = doc_repo.get_by_id(document_id)
        if not doc:
            return jsonify({'error': 'Document not found'}), 404

        subject   = doc.get('subject')
        file_path = doc.get('file_path')

        if not file_path:
            return jsonify({'error': 'Original file path not recorded; cannot reindex'}), 422

        import os
        if not os.path.exists(file_path):
            return jsonify({'error': f'Original file not found at {file_path}'}), 422

        # Step 1 – clear existing vectors
        try:
            removed = vector_store.delete_document(subject, document_id)
            logger.info("Reindex: removed %d vectors for %s", removed, document_id)
        except Exception as e:
            logger.warning("Reindex: could not delete existing vectors for %s: %s", document_id, e)

        # Step 2 – clear FTS entries
        try:
            db_manager = current_app.config['DB_MANAGER']
            from models.fts_repository import FTSRepository
            FTSRepository(db_manager).delete_document(document_id)
        except Exception as e:
            logger.warning("Reindex: could not clear FTS for %s: %s", document_id, e)

        # Step 3 – reset status and clear hash so queue processes without duplicate check
        doc_repo.update_status(document_id, 'pending')
        try:
            doc_repo.update_file_hash(document_id, None)
        except Exception:
            pass  # update_file_hash may not exist on all repo versions; non-fatal

        # Step 4 – enqueue
        from task_queue.indexing_queue import indexing_queue
        from services.indexing_service import IndexingService

        indexing_service = IndexingService(
            document_repo=doc_repo,
            vector_store=vector_store,
            fts_repo=current_app.config.get('FTS_REPO'),
        )
        # Build job payload matching indexing_queue expectations
        job = {
            'document_id': document_id,
            'file_path':   file_path,
            'subject':     subject,
            'original_filename': doc.get('filename', ''),
            'bypass_hash': True,
        }
        indexing_queue.enqueue(job)
        logger.info("Reindex job enqueued for document %s", document_id)

        return jsonify({
            'message':     'Reindex job queued',
            'document_id': document_id,
            'status':      'pending',
        }), 202

    except Exception as e:
        logger.exception("Unexpected error reindexing document %s", document_id)
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/upload', methods=['POST'])
@require_admin
def upload_files():
    """Accept multiple files and subject, save to uploads/<subject>/ and enqueue indexing."""
    subject = request.form.get('subject')
    if not subject:
        return jsonify({'error': 'Subject is required'}), 400
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400

    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': 'No files selected'}), 400

    upload_folder = current_app.config['APP_CONFIG'].UPLOAD_FOLDER
    subject_folder = upload_folder / subject
    subject_folder.mkdir(parents=True, exist_ok=True)

    indexing_queue = current_app.config['INDEXING_QUEUE']
    db_repo = current_app.config['DOCUMENT_REPO']
    vector_store = current_app.config['VECTOR_STORE']
    db_manager = current_app.config['DB_MANAGER']
    chunk_size = current_app.config.get('CHUNK_SIZE', 500)
    overlap = current_app.config.get('OVERLAP', 100)

    job_ids = []
    for file in files:
        if file.filename == '':
            continue
        # Secure filename
        safe_name = secure_filename(file.filename)
        file_path = subject_folder / safe_name
        file.save(file_path)
        # Enqueue indexing
        indexing_queue.enqueue(
            _index_file_task,
            file_path, safe_name, subject,
            db_repo, vector_store, db_manager, chunk_size, overlap
        )
        job_ids.append(safe_name)

    return jsonify({'message': f'{len(job_ids)} files queued', 'files': job_ids}), 202

def _index_file_task(file_path, original_filename, subject, db_repo, vector_store, db_manager, chunk_size, overlap):
    from services.indexing_service import IndexingService
    try:
        indexing_service = IndexingService(db_repo, vector_store, db_manager, chunk_size, overlap)
        indexing_service.index_document(file_path, original_filename, subject)
    except Exception as e:
        logger.exception("Indexing failed for %s: %s", file_path, e)