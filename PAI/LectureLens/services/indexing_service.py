"""Orchestrates the full document indexing pipeline."""
import logging
from pathlib import Path
import uuid

from services.document_parser import parse_document
from services.chunking_service import ChunkingService
from services.embedding_service import embedding_service
from services.vector_store import VectorStore
from models.document_repository import DocumentRepository
from models.fts_repository import FTSRepository
from utils.hashing import compute_sha256

logger = logging.getLogger(__name__)

class IndexingService:
    def __init__(self, db_repo: DocumentRepository, vector_store: VectorStore,
                 db_manager, chunk_size: int = 500, overlap: int = 100):
        self.db_repo = db_repo
        self.vector_store = vector_store
        self.fts_repo = FTSRepository(db_manager)
        self.chunker = ChunkingService(chunk_size=chunk_size, overlap=overlap)

    def index_document(self, file_path: Path, original_filename: str, subject: str) -> str:
        """
        Full indexing pipeline: parse, chunk, embed, store vectors, update DB.
        Returns document_id.
        """
        # 1. Hash file for duplicate detection
        file_hash = compute_sha256(file_path)
        existing = self.db_repo.get_by_hash(file_hash)
        if existing:
            raise ValueError(f"Duplicate document already exists: {existing['document_id']}")

        # 2. Parse document
        try:
            parsed = parse_document(file_path)
        except Exception as e:
            raise Exception(f"Parsing failed: {e}")

        pages = parsed['pages']
        metadata = parsed['metadata']

        # 3. Create DB entry (status='processing')
        doc_id = str(uuid.uuid4())
        self.db_repo.create(
            filename=original_filename,
            file_hash=file_hash,
            subject=subject,
            page_count=metadata['page_count'],
            status='processing',
            document_id=doc_id
        )

        try:
            # 4. Chunk pages
            chunks = self.chunker.chunk_document(pages)
            if not chunks:
                raise ValueError("No text chunks extracted from document.")

            # 4b. Insert chunks into FTS (keyword search)
            for chunk in chunks:
                self.fts_repo.insert_chunk(
                    chunk_id=chunk['chunk_id'],
                    text=chunk['text'],
                    document_id=doc_id,
                    page_num=chunk['page_num']
                )

            # 5. Generate embeddings for chunks
            enriched_chunks = embedding_service.embed_chunks(chunks)

            # 6. Add document_id, filename to each chunk metadata
            for chunk in enriched_chunks:
                chunk['document_id'] = doc_id
                chunk['filename'] = original_filename

            # 7. Store in vector store (per subject)
            self.vector_store.add_chunks(subject, enriched_chunks)

            # 8. Update DB status to 'completed'
            self.db_repo.update_status(doc_id, 'completed')
            logger.info("Successfully indexed document %s (%s)", doc_id, original_filename)
            return doc_id

        except Exception as e:
            # Mark as failed and re-raise
            self.db_repo.update_status(doc_id, 'failed')
            logger.exception("Indexing failed for document %s: %s", doc_id, e)
            raise