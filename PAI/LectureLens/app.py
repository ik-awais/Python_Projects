"""Flask application factory."""
import logging
import atexit
from flask import Flask
from config import Config
from utils.logger import setup_logging
from models.database import DatabaseManager

# Import new components (no indexing_queue here)
from routes.upload_routes import upload_bp
from services.vector_store import VectorStore

def create_app():
    """Create and configure Flask app."""
    # Load config (validates env vars)
    config = Config.from_env()

    # Setup logging first
    logger = setup_logging(config.LOG_FILE, log_level="INFO")
    logger.info("Starting LectureLens application")

    # Initialize Flask
    app = Flask(__name__)
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['DEBUG'] = config.DEBUG

    # Attach config to app for use in routes
    app.config['APP_CONFIG'] = config

    # Initialize database (creates tables)
    db_manager = DatabaseManager(config.DATABASE_PATH)
    from models.document_repository import DocumentRepository
    from models.conversation_repository import ConversationRepository
    from models.subject_repository import SubjectRepository
    from models.session_repository import SessionRepository

    app.config['DOCUMENT_REPO'] = DocumentRepository(db_manager)
    app.config['CONVERSATION_REPO'] = ConversationRepository(db_manager)
    app.config['SUBJECT_REPO'] = SubjectRepository(db_manager)
    app.config['SESSION_REPO'] = SessionRepository(db_manager)

    # Seed default subjects
    subject_repo = app.config['SUBJECT_REPO']
    subjects = subject_repo.ensure_default_subjects()
    logger.info("Default subjects seeded: %s", [s['name'] for s in subjects])
    app.config['DB_MANAGER'] = db_manager

    # Vector store
    from services.vector_store import VectorStore
    vector_store = VectorStore(config.CHROMA_PATH, embedding_dimension=384)
    app.config['VECTOR_STORE'] = vector_store

    # FTS and Search Service
    from models.fts_repository import FTSRepository
    from services.search_service import SearchService
    fts_repo = FTSRepository(db_manager)
    search_service = SearchService(vector_store, fts_repo)
    app.config['SEARCH_SERVICE'] = search_service
    app.config['FTS_REPO'] = fts_repo  # exposed for admin reindex

    # LLM Clients (NVIDIA only)
    from services.llm_client import NVIDIAClient
    from services.rag_pipeline import RAGPipeline
    nvidia_client = NVIDIAClient(config.NVIDIA_API_KEY)
    rag_pipeline = RAGPipeline(search_service, nvidia_client=nvidia_client)
    app.config['RAG_PIPELINE'] = rag_pipeline

    # Register blueprints
    from routes.upload_routes import upload_bp
    from routes.search_routes import search_bp
    from routes.chat_routes import chat_bp
    from routes.subjects_routes import subjects_bp
    from routes.admin_routes import admin_bp

    app.register_blueprint(upload_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(subjects_bp)
    app.register_blueprint(admin_bp)

    # Initialize indexing queue with configured workers
    from task_queue.indexing_queue import init_queue, get_queue
    init_queue(max_workers=config.INDEXING_WORKERS)
    indexing_queue = get_queue()
    app.config['INDEXING_QUEUE'] = indexing_queue
    atexit.register(indexing_queue.stop)

    # Initialize folder watcher if enabled
    if config.WATCH_FOLDER_ENABLED:
        from task_queue.folder_watcher import FolderWatcher
        watcher = FolderWatcher(
            base_upload_folder=config.UPLOAD_FOLDER,
            indexing_queue=indexing_queue,
            document_repo=app.config['DOCUMENT_REPO'],
            vector_store=app.config['VECTOR_STORE'],
            db_manager=app.config['DB_MANAGER'],
            chunk_size=config.CHUNK_SIZE,
            overlap=config.OVERLAP,
            scan_interval=config.WATCH_FOLDER_INTERVAL_SECONDS
        )
        watcher.start()
        atexit.register(watcher.stop)
        logger.info("Folder watcher started (interval=%ds)", config.WATCH_FOLDER_INTERVAL_SECONDS)

    # Health and root routes
    @app.route('/health', methods=['GET'])
    def health():
        return {"status": "healthy"}, 200

    @app.route('/', methods=['GET'])
    def index():
        from flask import render_template
        return render_template('chat.html')

    logger.info("Application ready")
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=app.config['DEBUG'])