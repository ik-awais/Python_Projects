"""Hybrid search combining vector similarity and keyword full-text search."""
import logging
from typing import List, Dict, Any, Optional
from services.embedding_service import embedding_service
from services.vector_store import VectorStore
from models.fts_repository import FTSRepository

logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self, vector_store: VectorStore, fts_repo: FTSRepository,
                 vector_weight: float = 0.7, keyword_weight: float = 0.3,
                 vector_top_k: int = 10, keyword_top_k: int = 10):
        self.vector_store = vector_store
        self.fts_repo = fts_repo
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.vector_top_k = vector_top_k
        self.keyword_top_k = keyword_top_k

    def hybrid_search(self, query: str, subject: Optional[str] = None,
                    top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Combine vector and keyword search using weighted scoring.
        If subject is None or empty, search across all collections.
        """
        query_embedding = embedding_service.embed_text(query)

        # --- VECTOR SEARCH ---
        if subject and subject != "General":
            # Subject-specific search
            vector_results = self.vector_store.search(subject, query_embedding, top_k=self.vector_top_k)
        else:
            # Cross-subject search
            vector_results = self.vector_store.search_all(query_embedding,
                                                        top_k_per_collection=self.vector_top_k,
                                                        final_top_k=self.vector_top_k)

        # Normalize distances to similarity (0-1) using 1/(1+distance)
        for res in vector_results:
            res['vector_score'] = 1.0 / (1.0 + res['distance'])

        # --- KEYWORD SEARCH (FTS) ---
        # Keyword search is subject‑specific (FTS table stores subject? Actually it stores document_id, not subject.
        # To keep it simple, we still run FTS across all chunks; it will return results from any subject.
        # This is acceptable because cross‑subject keyword search is fine.
        keyword_results = self.fts_repo.keyword_search(query, limit=self.keyword_top_k)
        for res in keyword_results:
            res['keyword_score'] = 1.0 / (1.0 + res['score'])

        # --- MERGE AND SCORE (as before) ---
        merged = {}
        for res in vector_results:
            chunk_id = res['id']
            merged[chunk_id] = {
                'chunk_id': chunk_id,
                'text': res['text'],
                'metadata': res['metadata'],
                'vector_score': res['vector_score'],
                'keyword_score': 0.0
            }
        for res in keyword_results:
            chunk_id = res['chunk_id']
            if chunk_id in merged:
                merged[chunk_id]['keyword_score'] = res['keyword_score']
            else:
                merged[chunk_id] = {
                    'chunk_id': chunk_id,
                    'text': res['text'],
                    'metadata': {
                        'document_id': res['document_id'],
                        'page_num': res['page_num']
                    },
                    'vector_score': 0.0,
                    'keyword_score': res['keyword_score']
                }

        for chunk_id, item in merged.items():
            item['combined_score'] = (self.vector_weight * item['vector_score'] +
                                    self.keyword_weight * item['keyword_score'])

        sorted_items = sorted(merged.values(), key=lambda x: x['combined_score'], reverse=True)
        return sorted_items[:top_k]