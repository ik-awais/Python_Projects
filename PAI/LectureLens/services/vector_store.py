"""ChromaDB vector store with per‑subject collections."""
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

import chromadb
from chromadb.config import Settings
from chromadb.errors import NotFoundError
logger = logging.getLogger(__name__)

class VectorStore:
    """Wrapper for ChromaDB persistent client with subject‑based collections."""

    def __init__(self, persist_directory: Path, embedding_dimension: int = 384):
        """
        Args:
            persist_directory: Directory to store ChromaDB data (e.g., ./database/chroma).
            embedding_dimension: Expected dimension of embeddings (default 384 for BGE-small).
        """
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self._client = None
        self._embedding_dimension = embedding_dimension

    @property
    def client(self):
        """Lazy initialize ChromaDB client (singleton)."""
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(anonymized_telemetry=False),
            )
            logger.info("ChromaDB client initialized at %s", self.persist_directory)
        return self._client

    def _get_collection_name(self, subject: str) -> str:
        """Convert subject name to collection name."""
        slug = subject.lower().replace(' ', '_')
        return f"lecturelens_{slug}"

    def _get_or_create_collection(self, subject: str):
        """Get existing collection or create new one."""
        name = self._get_collection_name(subject)
        try:
            collection = self.client.get_collection(name)
        except (NotFoundError, ValueError):
            # Collection does not exist; create it
            collection = self.client.create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}  # cosine similarity
            )
            logger.info("Created new collection: %s", name)
        return collection

    def add_chunks(self, subject: str, chunks: List[Dict[str, Any]]) -> None:
        """
        Add enriched chunks to the subject's collection.
        Each chunk must contain:
            - embedding: List[float]
            - chunk_id: str
            - document_id: str
            - filename: str
            - page_num: int
            - text: str
            - chunk_index: int
            - start_char: int
            - end_char: int
        """
        if not chunks:
            return

        # Validate embeddings dimension
        for chunk in chunks:
            emb = chunk.get('embedding')
            if emb is None:
                raise ValueError(f"Chunk missing 'embedding': {chunk.get('chunk_id')}")
            if len(emb) != self._embedding_dimension:
                raise ValueError(
                    f"Embedding dimension mismatch: expected {self._embedding_dimension}, "
                    f"got {len(emb)} for chunk {chunk.get('chunk_id')}"
                )

        collection = self._get_or_create_collection(subject)

        # Prepare data for ChromaDB
        ids = [chunk['chunk_id'] for chunk in chunks]
        embeddings = [chunk['embedding'] for chunk in chunks]
        metadatas = []
        documents = []

        for chunk in chunks:
            # Metadata that ChromaDB can filter on
            meta = {
                "document_id": chunk['document_id'],
                "filename": chunk['filename'],
                "page_num": chunk['page_num'],
                "chunk_index": chunk['chunk_index'],
                "start_char": chunk['start_char'],
                "end_char": chunk['end_char'],
            }
            metadatas.append(meta)
            documents.append(chunk['text'])  # store text for retrieval

        # Add in batches to avoid overwhelming (optional, ChromaDB handles list)
        collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )
        logger.info("Added %d chunks to collection '%s'", len(chunks), collection.name)

    def search(self, subject: str, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar chunks in the subject's collection.
        Returns list of dicts with keys: id, text, metadata, distance.
        """
        collection_name = self._get_collection_name(subject)
        try:
            collection = self.client.get_collection(collection_name)
        except ValueError:
            logger.warning("Collection '%s' does not exist. Returning empty results.", collection_name)
            return []

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        # Flatten the nested lists (chromadb returns lists of lists for batch queries)
        ids = results['ids'][0] if results['ids'] else []
        docs = results['documents'][0] if results['documents'] else []
        metadatas = results['metadatas'][0] if results['metadatas'] else []
        distances = results['distances'][0] if results['distances'] else []

        output = []
        for idx, chunk_id in enumerate(ids):
            output.append({
                "id": chunk_id,
                "text": docs[idx],
                "metadata": metadatas[idx],
                "distance": distances[idx],
            })
        return output

    def delete_document(self, subject: str, document_id: str) -> int:
        """
        Delete all chunks belonging to a specific document_id from the subject's collection.
        Returns number of chunks deleted.
        """
        collection_name = self._get_collection_name(subject)
        try:
            collection = self.client.get_collection(collection_name)
        except ValueError:
            logger.warning("Collection '%s' does not exist. Nothing deleted.", collection_name)
            return 0

        # First, get all chunk ids for this document_id
        # ChromaDB doesn't support metadata filtering in delete directly; we need to query first.
        # We can use get() with where filter.
        try:
            result = collection.get(where={"document_id": document_id})
            ids_to_delete = result['ids']
        except Exception as e:
            logger.error("Failed to retrieve chunks for document %s: %s", document_id, e)
            return 0

        if not ids_to_delete:
            logger.info("No chunks found for document %s in collection %s", document_id, collection_name)
            return 0

        collection.delete(ids=ids_to_delete)
        logger.info("Deleted %d chunks for document %s from collection %s", len(ids_to_delete), document_id, collection_name)
        return len(ids_to_delete)

    def delete_subject_collection(self, subject: str) -> bool:
        """
        Delete the entire collection for a subject.
        Returns True if deleted, False if not found.
        """
        name = self._get_collection_name(subject)
        try:
            self.client.delete_collection(name)
            logger.info("Deleted collection: %s", name)
            return True
        except ValueError:
            logger.warning("Collection %s does not exist", name)
            return False

    def get_subject_collections(self) -> List[str]:
        """Return list of existing subject collection names (human readable)."""
        collections = self.client.list_collections()
        subjects = []
        for col in collections:
            name = col.name
            if name.startswith("lecturelens_"):
                # Extract subject slug and convert back to title case
                slug = name.replace("lecturelens_", "")
                subject = slug.replace('_', ' ').title()
                subjects.append(subject)
        return subjects