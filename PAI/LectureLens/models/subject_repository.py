"""Repository for subjects table with seeding."""
from typing import Dict, List, Optional
from models.database import DatabaseManager
import uuid

DEFAULT_SUBJECTS = ["AI", "Operating Systems", "DSA", "Databases", "Computer Networks"]

class SubjectRepository:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def create(self, name: str) -> str:
        """Create a subject, return subject_id."""
        subject_id = str(uuid.uuid4())
        self.db.execute(
            "INSERT OR IGNORE INTO subjects (subject_id, name) VALUES (?, ?)",
            (subject_id, name)
        )
        # If already exists, get existing id
        existing = self.get_by_name(name)
        return existing["subject_id"] if existing else subject_id

    def get_by_name(self, name: str) -> Optional[Dict]:
        rows = self.db.fetch_all(
            "SELECT * FROM subjects WHERE name = ?", (name,)
        )
        return rows[0] if rows else None

    def get_all(self) -> List[Dict]:
        return self.db.fetch_all("SELECT * FROM subjects ORDER BY name")

    def delete(self, subject_id: str) -> None:
        self.db.execute("DELETE FROM subjects WHERE subject_id = ?", (subject_id,))

    def ensure_default_subjects(self) -> List[Dict]:
        """Insert default subjects if missing, return all subjects."""
        for name in DEFAULT_SUBJECTS:
            self.create(name)
        return self.get_all()