"""Full-text search using SQLite FTS5."""
import logging
import re
from models.database import DatabaseManager

logger = logging.getLogger(__name__)

class FTSRepository:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self._init_fts()

    def _init_fts(self):
        """Create virtual table for full-text search if not exists."""
        self.db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                chunk_id,
                text,
                document_id,
                page_num
            )
        """)
        logger.info("FTS5 virtual table 'chunks_fts' ready")

    def insert_chunk(self, chunk_id: str, text: str, document_id: str, page_num: int):
        """Insert or replace a chunk into FTS index."""
        self.db.execute(
            "INSERT OR REPLACE INTO chunks_fts (chunk_id, text, document_id, page_num) VALUES (?, ?, ?, ?)",
            (chunk_id, text, document_id, page_num)
        )

    def delete_document_chunks(self, document_id: str):
        """Delete all chunks belonging to a document from FTS index."""
        rows = self.db.fetch_all(
            "SELECT chunk_id FROM chunks_fts WHERE document_id = ?", (document_id,)
        )
        for row in rows:
            self.db.execute("DELETE FROM chunks_fts WHERE chunk_id = ?", (row['chunk_id'],))


    def keyword_search(self, query: str, limit: int = 10) -> list:
        """
        Perform keyword search using FTS5 MATCH.
        - Removes punctuation that FTS5 cannot handle (?, !, ., etc.)
        - Escapes double quotes.
        - Uses direct formatting for LIMIT (no placeholder).
        """
        # Remove characters that break FTS5 MATCH syntax
        # Keep only letters, numbers, spaces, and underscores
        safe_query = re.sub(r'[^\w\s]', ' ', query)
        # Collapse multiple spaces
        safe_query = ' '.join(safe_query.split())
        if not safe_query:
            return []

        # Escape double quotes (still needed for exact phrases)
        safe_query = safe_query.replace('"', '""')

        # Build SQL with literal limit (no placeholder)
        sql = f"""
            SELECT chunk_id, text, document_id, page_num,
                rank as score
            FROM chunks_fts
            WHERE chunks_fts MATCH '{safe_query}'
            ORDER BY rank
            LIMIT {int(limit)}
        """
        # fetch_all expects a tuple of parameters – but we have none now
        # So we call fetch_all with an empty tuple
        return self.db.fetch_all(sql, ())