"""Flask application factory."""
import logging
import atexit
from flask import Flask
from config import Config
from utils.logger import setup_logging
from models.database import DatabaseManager

# Import new components
from routes.upload_routes import upload_bp
from services.vector_store import VectorStore
from task_queue.indexing_queue import indexing_queue
from models.fts_repository import FTSRepository
from services.search_service import SearchService


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

    # ---------------------------------------------------------
    # NEW COMPONENTS: Vector Store, Routes, and Queue
    # ---------------------------------------------------------
    
    # Create vector store (persistent)
    # Ensure CHROMA_PATH is defined in your config.py
    vector_store = VectorStore(config.CHROMA_PATH, embedding_dimension=384)
    app.config['VECTOR_STORE'] = vector_store

    # Register blueprint
    app.register_blueprint(upload_bp)

    # Start background queue worker
    indexing_queue.start()

    # Add cleanup on shutdown
    atexit.register(indexing_queue.stop)
    
    fts_repo = FTSRepository(db_manager)
    search_service = SearchService(vector_store, fts_repo)
    app.config['SEARCH_SERVICE'] = search_service

    from routes.search_routes import search_bp
    app.register_blueprint(search_bp)
    
    # ---------------------------------------------------------

    # Register health check route 
    @app.route('/health', methods=['GET'])
    def health():
        return {"status": "healthy"}, 200

    @app.route('/', methods=['GET'])
    def index():
        return {"message": "LectureLens API Running"}, 200

    logger.info("Application ready")

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=app.config['DEBUG'])