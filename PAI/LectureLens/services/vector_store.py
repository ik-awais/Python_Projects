"""ChromaDB vector store with per‑subject collections."""
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

import chromadb
from chromadb.errors import NotFoundError
from chromadb.config import Settings

logger = logging.getLogger(__name__)

class VectorStore:
    """Wrapper for ChromaDB persistent client with subject‑based collections."""

    def __init__(self, persist_directory: Path, embedding_dimension: int = 384):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self._client = None
        self._embedding_dimension = embedding_dimension

    @property
    def client(self):
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(anonymized_telemetry=False),
            )
            logger.info("ChromaDB client initialized at %s", self.persist_directory)
        return self._client

    def _get_collection_name(self, subject: str) -> str:
        slug = subject.lower().replace(' ', '_')
        return f"lecturelens_{slug}"

    def _get_or_create_collection(self, subject: str):
        name = self._get_collection_name(subject)
        try:
            collection = self.client.get_collection(name)
        except NotFoundError:
            collection = self.client.create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("Created new collection: %s", name)
        return collection

    def add_chunks(self, subject: str, chunks: List[Dict[str, Any]]) -> None:
        if not chunks:
            return
        for chunk in chunks:
            emb = chunk.get('embedding')
            if emb is None:
                raise ValueError(f"Chunk missing 'embedding': {chunk.get('chunk_id')}")
            if len(emb) != self._embedding_dimension:
                raise ValueError(f"Embedding dimension mismatch: expected {self._embedding_dimension}, got {len(emb)}")

        collection = self._get_or_create_collection(subject)
        ids = [chunk['chunk_id'] for chunk in chunks]
        embeddings = [chunk['embedding'] for chunk in chunks]
        metadatas = []
        documents = []
        for chunk in chunks:
            metadatas.append({
                "document_id": chunk['document_id'],
                "filename": chunk['filename'],
                "page_num": chunk['page_num'],
                "chunk_index": chunk['chunk_index'],
                "start_char": chunk['start_char'],
                "end_char": chunk['end_char'],
            })
            documents.append(chunk['text'])
        collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)
        logger.info("Added %d chunks to collection '%s'", len(chunks), collection.name)

    def search(self, subject: str, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        collection_name = self._get_collection_name(subject)
        try:
            collection = self.client.get_collection(collection_name)
        except NotFoundError:
            logger.warning("Collection '%s' does not exist. Returning empty results.", collection_name)
            return []

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
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
        collection_name = self._get_collection_name(subject)
        try:
            collection = self.client.get_collection(collection_name)
        except NotFoundError:
            logger.warning("Collection '%s' does not exist. Nothing deleted.", collection_name)
            return 0
        try:
            result = collection.get(where={"document_id": document_id})
            ids_to_delete = result['ids']
        except Exception as e:
            logger.error("Failed to retrieve chunks for document %s: %s", document_id, e)
            return 0
        if not ids_to_delete:
            return 0
        collection.delete(ids=ids_to_delete)
        logger.info("Deleted %d chunks for document %s from collection %s", len(ids_to_delete), document_id, collection_name)
        return len(ids_to_delete)

    def delete_subject_collection(self, subject: str) -> bool:
        name = self._get_collection_name(subject)
        try:
            self.client.delete_collection(name)
            logger.info("Deleted collection: %s", name)
            return True
        except NotFoundError:
            logger.warning("Collection %s does not exist", name)
            return False

    def get_subject_collections(self) -> List[str]:
        collections = self.client.list_collections()
        subjects = []
        for col in collections:
            name = col.name
            if name.startswith("lecturelens_"):
                slug = name.replace("lecturelens_", "")
                subject = slug.replace('_', ' ').title()
                subjects.append(subject)
        return subjects
    def search_all(self, query_embedding: List[float], top_k_per_collection: int = 5, final_top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Search across all subject collections.
        Returns merged results sorted by distance (ascending).
        """
        all_results = []
        for collection in self.client.list_collections():
            # Only consider our lecturelens_* collections
            if not collection.name.startswith("lecturelens_"):
                continue
            try:
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k_per_collection,
                    include=["documents", "metadatas", "distances"],
                )
                ids = results['ids'][0] if results['ids'] else []
                docs = results['documents'][0] if results['documents'] else []
                metas = results['metadatas'][0] if results['metadatas'] else []
                dists = results['distances'][0] if results['distances'] else []
                for idx, chunk_id in enumerate(ids):
                    all_results.append({
                        "id": chunk_id,
                        "text": docs[idx],
                        "metadata": metas[idx],
                        "distance": dists[idx],
                    })
            except Exception as e:
                logger.warning("Error searching collection %s: %s", collection.name, e)

        # Sort by distance (lower = more similar) and return top final_top_k
        all_results.sort(key=lambda x: x['distance'])
        return all_results[:final_top_k]