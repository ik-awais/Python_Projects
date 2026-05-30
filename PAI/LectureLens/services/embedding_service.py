"""Embedding service using BAAI/bge-small-en-v1.5 with lazy loading and caching."""
import logging
from functools import lru_cache
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Global singleton instance (loaded on first use)
_embedding_model = None
_model_dimension = None

def get_embedding_model():
    """Lazy load the sentence‑transformer model."""
    global _embedding_model, _model_dimension
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError("sentence-transformers not installed. Run: pip install sentence-transformers")
        logger.info("Loading embedding model: BAAI/bge-small-en-v1.5")
        _embedding_model = SentenceTransformer("BAAI/bge-small-en-v1.5")
        _model_dimension = _embedding_model.get_embedding_dimension()
        logger.info("Model loaded. Embedding dimension: %d", _model_dimension)
    return _embedding_model, _model_dimension

class EmbeddingService:
    def __init__(self):
        """Initialize service (model loaded lazily on first use)."""
        self._model = None
        self._dimension = None

    @property
    def model(self):
        if self._model is None:
            self._model, self._dimension = get_embedding_model()
        return self._model

    @property
    def dimension(self):
        if self._dimension is None:
            _, self._dimension = get_embedding_model()
        return self._dimension

    @lru_cache(maxsize=1024)
    def embed_text(self, text: str) -> List[float]:
        """
        Embed a single text string. Results are cached (LRU).
        Returns a list of floats.
        """
        if not text or not text.strip():
            logger.warning("Empty text provided to embed_text")
            return [0.0] * self.dimension
        embedding = self.model.encode(text, convert_to_numpy=True).tolist()
        # Validate dimension
        if len(embedding) != self.dimension:
            raise RuntimeError(f"Unexpected embedding dimension: {len(embedding)} vs {self.dimension}")
        return embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a batch of text strings. No per‑item caching for batch.
        Returns a list of embedding vectors (list of floats each).
        """
        if not texts:
            return []
        # Filter out empty strings to avoid wasting compute
        non_empty = [(i, t) for i, t in enumerate(texts) if t and t.strip()]
        indices = [i for i, _ in non_empty]
        valid_texts = [t for _, t in non_empty]
        if not valid_texts:
            return [[0.0] * self.dimension for _ in texts]

        embeddings = self.model.encode(valid_texts, convert_to_numpy=True)
        # Convert to list of lists
        vectors = [emb.tolist() for emb in embeddings]
        # Validate dimension for each
        for vec in vectors:
            if len(vec) != self.dimension:
                raise RuntimeError(f"Batch embedding dimension mismatch: {len(vec)} vs {self.dimension}")

        # Re‑insert empty vectors for original empty strings
        result = []
        vec_idx = 0
        for i in range(len(texts)):
            if i in indices:
                result.append(vectors[vec_idx])
                vec_idx += 1
            else:
                result.append([0.0] * self.dimension)
        return result

    def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich a list of chunk dicts with an 'embedding' field.
        Input chunks must have a 'text' key.
        Returns a new list of dicts (original metadata + embedding).
        """
        if not chunks:
            return []

        texts = [chunk.get('text', '') for chunk in chunks]
        embeddings = self.embed_batch(texts)

        enriched = []
        for chunk, emb in zip(chunks, embeddings):
            new_chunk = chunk.copy()
            new_chunk['embedding'] = emb
            enriched.append(new_chunk)
        return enriched

# Convenience singleton for direct import
embedding_service = EmbeddingService()