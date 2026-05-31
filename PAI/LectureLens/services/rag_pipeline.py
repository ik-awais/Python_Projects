"""RAG pipeline: retrieve, build prompt, call LLM, extract citations."""
import logging
from typing import List, Dict, Any, Optional

from services.search_service import SearchService
from services.llm_client import GeminiClient, NVIDIAClient

logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self, search_service: SearchService,
                 gemini_client: Optional[GeminiClient] = None,
                 nvidia_client: Optional[NVIDIAClient] = None):
        self.search_service = search_service
        self.gemini = gemini_client
        self.nvidia = nvidia_client

    def _build_context(self, chunks: List[Dict]) -> str:
        """Combine retrieved chunks into context string with citations."""
        context_parts = []
        for chunk in chunks:
            meta = chunk['metadata']
            filename = meta.get('filename', 'unknown')
            page = meta.get('page_num', '?')
            context_parts.append(f"[Source: {filename}, Page {page}]\n{chunk['text']}\n")
        return "\n".join(context_parts)

    def _extract_citations(self, chunks: List[Dict]) -> List[Dict]:
        """Return unique citation entries: filename, page_num."""
        seen = set()
        citations = []
        for chunk in chunks:
            meta = chunk['metadata']
            filename = meta.get('filename', 'unknown')
            page = meta.get('page_num', '?')
            key = (filename, page)
            if key not in seen:
                seen.add(key)
                citations.append({"filename": filename, "page": page})
        return citations

    def answer(self, question: str, subject: Optional[str] = None,
               top_k: int = 5) -> Dict[str, Any]:
        """
        Run RAG: retrieve, call LLM (with fallback), return answer and citations.
        """
        # 1. Retrieve relevant chunks
        chunks = self.search_service.hybrid_search(question, subject, top_k)
        if not chunks:
            return {
                "answer": "I couldn't find any relevant information in the documents.",
                "citations": [],
                "retrieved_chunks": []
            }

        # 2. Build context and prompt
        context = self._build_context(chunks)
        prompt = f"""You are a helpful study assistant. Use only the provided context to answer the question. If the answer is not in the context, say "I don't have enough information about that."

Context:
{context}

Question: {question}

Answer with citations (source filename and page number):"""

        # 3. Try LLM calls with fallback
        answer_text = None
        if self.gemini:
            answer_text = self.gemini.generate(prompt)
        if not answer_text and self.nvidia:
            answer_text = self.nvidia.generate(prompt)
        if not answer_text:
            # Fallback to retrieval-only response
            answer_text = "Based on the retrieved context:\n\n" + "\n".join([chunk['text'] for chunk in chunks])

        # 4. Extract citations from retrieved chunks
        citations = self._extract_citations(chunks)

        return {
            "answer": answer_text,
            "citations": citations,
            "retrieved_chunks": chunks  # optional, for debugging
        }