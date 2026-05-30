"""Repository for documents table."""
from typing import Dict, List, Optional
from models.database import DatabaseManager
import uuid
from datetime import datetime

class DocumentRepository:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def create(self, filename: str, file_hash: str, subject: str,
           page_count: Optional[int] = None, status: str = "pending",
           document_id: Optional[str] = None) -> str:
        doc_id = document_id if document_id else str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        self.db.execute(
            """INSERT INTO documents
            (document_id, filename, hash, subject, upload_time, page_count, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (doc_id, filename, file_hash, subject, now, page_count, status)
        )
        return doc_id

    def get_by_id(self, doc_id: str) -> Optional[Dict]:
        rows = self.db.fetch_all(
            "SELECT * FROM documents WHERE document_id = ?", (doc_id,)
        )
        return rows[0] if rows else None

    def get_by_hash(self, file_hash: str) -> Optional[Dict]:
        rows = self.db.fetch_all(
            "SELECT * FROM documents WHERE hash = ?", (file_hash,)
        )
        return rows[0] if rows else None

    def get_by_subject(self, subject: str) -> List[Dict]:
        return self.db.fetch_all(
            "SELECT * FROM documents WHERE subject = ? ORDER BY upload_time DESC",
            (subject,)
        )

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        return self.db.fetch_all(
            "SELECT * FROM documents ORDER BY upload_time DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )

    def update_status(self, doc_id: str, status: str) -> None:
        self.db.execute(
            "UPDATE documents SET status = ? WHERE document_id = ?",
            (status, doc_id)
        )

    def delete(self, doc_id: str) -> None:
        self.db.execute("DELETE FROM documents WHERE document_id = ?", (doc_id,))

    def count_by_subject(self, subject: str) -> int:
        rows = self.db.fetch_all(
            "SELECT COUNT(*) as cnt FROM documents WHERE subject = ?", (subject,)
        )
        return rows[0]["cnt"] if rows else 0

    def total_count(self) -> int:
        rows = self.db.fetch_all("SELECT COUNT(*) as cnt FROM documents")
        return rows[0]["cnt"] if rows else 0