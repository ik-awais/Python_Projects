"""Repository for sessions table."""
from typing import Dict, Optional
from models.database import DatabaseManager
import uuid
from datetime import datetime

class SessionRepository:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def create(self) -> str:
        """Create a new session, return session_id."""
        session_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        self.db.execute(
            "INSERT INTO sessions (session_id, created_at) VALUES (?, ?)",
            (session_id, now)
        )
        return session_id

    def get(self, session_id: str) -> Optional[Dict]:
        rows = self.db.fetch_all(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        )
        return rows[0] if rows else None

    def exists(self, session_id: str) -> bool:
        return self.get(session_id) is not None