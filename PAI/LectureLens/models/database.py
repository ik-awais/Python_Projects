"""SQLite connection manager with WAL mode and context managers."""
import sqlite3
from pathlib import Path
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Singleton-like wrapper for SQLite connections."""
    _instance = None

    def __new__(cls, db_path: Path):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: Path):
        if self._initialized:
            return
        self.db_path = db_path
        self._initialized = True
        self._init_database()

    def _init_database(self):
        """Create tables if they don't exist and enable WAL mode."""
        with self.get_connection() as conn:
            conn.executescript("""
                PRAGMA journal_mode=WAL;
                PRAGMA foreign_keys=ON;

                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    hash TEXT UNIQUE NOT NULL,
                    subject TEXT NOT NULL,
                    upload_time TEXT NOT NULL,
                    page_count INTEGER,
                    status TEXT DEFAULT 'pending'
                );

                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS subjects (
                    subject_id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_documents_filename ON documents(filename);
                CREATE INDEX IF NOT EXISTS idx_documents_subject ON documents(subject);
                CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp);
                CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at);
            """)
            logger.info("Database initialized at %s with WAL mode", self.db_path)

    @contextmanager
    def get_connection(self):
        """Yield a database connection, automatically commit/rollback."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute(self, query: str, params=()):
        """Execute a single query (INSERT, UPDATE, DELETE) and return cursor."""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor

    def fetch_all(self, query: str, params=()):
        """Execute SELECT and return all rows as list of dicts."""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def fetch_one(self, query: str, params=()):
        """Execute SELECT and return one row as dict or None."""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None