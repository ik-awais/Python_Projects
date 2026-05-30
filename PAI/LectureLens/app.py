"""Flask application factory."""
from flask import Flask
from config import Config
from utils.logger import setup_logging
from models.database import DatabaseManager
import logging

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

    # Register health check route (simple, for Phase 6 we'll add detailed checks)
    @app.route('/health', methods=['GET'])
    def health():
        return {"status": "healthy"}, 200

    logger.info("Application ready")

    return app

    @app.route('/', methods=['GET'])
    def index():
        return {"message": "LectureLens API Running"}, 200

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=app.config['DEBUG'])