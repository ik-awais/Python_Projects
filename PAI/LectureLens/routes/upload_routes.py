"""Upload endpoint blueprint with background indexing."""
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from pathlib import Path
import uuid
import logging

from utils.validators import is_allowed_file, is_file_size_within_limit
from services.indexing_service import IndexingService
from task_queue.indexing_queue import indexing_queue

upload_bp = Blueprint('upload', __name__)
logger = logging.getLogger(__name__)

@upload_bp.route('/upload', methods=['POST'])
def upload_document():
    """Accept file, validate, store temporarily, and enqueue indexing."""
    config = current_app.config['APP_CONFIG']
    max_size_mb = config.MAX_FILE_SIZE_MB
    allowed_extensions = config.ALLOWED_EXTENSIONS
    upload_folder = config.UPLOAD_FOLDER

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not is_allowed_file(file.filename, allowed_extensions):
        return jsonify({'error': f'File type not allowed. Allowed: {", ".join(allowed_extensions)}'}), 400

    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    if not is_file_size_within_limit(file_size, max_size_mb):
        return jsonify({'error': f'File too large. Max size: {max_size_mb} MB'}), 400

    subject = request.form.get('subject', 'General').strip()
    if not subject:
        subject = 'General'

    original_filename = secure_filename(file.filename)
    safe_filename = f"{uuid.uuid4().hex}_{original_filename}"
    file_path = upload_folder / safe_filename
    file.save(file_path)

    # Dependencies (safe to access inside request context)
    db_repo = current_app.config['DOCUMENT_REPO']
    vector_store = current_app.config['VECTOR_STORE']
    db_manager = current_app.config['DB_MANAGER']          # <-- NEW
    chunk_size = current_app.config.get('CHUNK_SIZE', 500)
    overlap = current_app.config.get('OVERLAP', 100)

    # Background task – uses module logger, not current_app
    def indexing_task(file_path, original_filename, subject, db_repo, vector_store, db_manager, chunk_size, overlap):
        try:
            indexing_service = IndexingService(db_repo, vector_store, db_manager, chunk_size, overlap)
            indexing_service.index_document(file_path, original_filename, subject)
        except Exception as e:
            logger.error("Background indexing failed for %s: %s", file_path.name, e)
            if file_path.exists():
                file_path.unlink()

    indexing_queue.enqueue(indexing_task, file_path, original_filename, subject,
                           db_repo, vector_store, db_manager, chunk_size, overlap)

    return jsonify({
        'message': 'Document upload accepted, indexing in background',
        'original_filename': original_filename,
        'subject': subject
    }), 202