"""Repository for conversations table."""
from typing import Dict, List, Optional
from models.database import DatabaseManager
import uuid
from datetime import datetime

class ConversationRepository:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def create(self, session_id: str, question: str, answer: str) -> str:
        conv_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        self.db.execute(
            """INSERT INTO conversations
               (conversation_id, session_id, timestamp, question, answer)
               VALUES (?, ?, ?, ?, ?)""",
            (conv_id, session_id, now, question, answer)
        )
        return conv_id

    def get_by_session(self, session_id: str, limit: int = 50) -> List[Dict]:
        return self.db.fetch_all(
            """SELECT * FROM conversations
               WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?""",
            (session_id, limit)
        )

    def get_all(self, limit: int = 100) -> List[Dict]:
        return self.db.fetch_all(
            "SELECT * FROM conversations ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )