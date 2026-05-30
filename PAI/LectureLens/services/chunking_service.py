"""Text chunking service with configurable size and overlap."""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ChunkingService:
    def __init__(self, chunk_size: int = 500, overlap: int = 100, respect_sentence_boundary: bool = True):
        if overlap >= chunk_size:
            raise ValueError("Overlap must be less than chunk_size")
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.respect_sentence_boundary = respect_sentence_boundary

    def chunk_document(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        all_chunks = []
        global_char_offset = 0
        global_chunk_index = 0

        for page in pages:
            page_num = page['page_num']
            text = page['text']
            if not text.strip():
                continue

            page_chunks = self._chunk_text(text, page_num, global_char_offset, global_chunk_index)
            for chunk in page_chunks:
                all_chunks.append(chunk)
                global_chunk_index += 1
                global_char_offset += len(text)

        return all_chunks

    def _chunk_text(self, text: str, page_num: int, start_offset: int, start_chunk_idx: int) -> List[Dict[str, Any]]:
        chunks = []
        text_len = len(text)
        if text_len == 0:
            return chunks

        pos = 0
        chunk_idx = start_chunk_idx

        while pos < text_len:
            # Determine end position
            end = min(pos + self.chunk_size, text_len)

            # Optional sentence boundary adjustment
            if self.respect_sentence_boundary and end < text_len:
                # Look for sentence end within next 200 chars
                for i in range(end, min(end + 200, text_len)):
                    if i < text_len - 1 and text[i] in '.!?' and text[i+1] in ' \n':
                        end = i + 1
                        break

            chunk_text = text[pos:end].strip()
            if chunk_text:
                chunks.append({
                    "chunk_id": f"page_{page_num}_chunk_{chunk_idx}",
                    "page_num": page_num,
                    "text": chunk_text,
                    "chunk_index": chunk_idx,
                    "start_char": start_offset + pos,
                    "end_char": start_offset + end,
                })

            # Advance position with overlap, but ensure progress
            next_pos = end - self.overlap
            if next_pos <= pos:
                # No progress → jump to end (avoids infinite loop)
                next_pos = end
            pos = next_pos
            chunk_idx += 1

            # Safety break (should not be needed, but guard against bugs)
            if pos >= text_len:
                break

        return chunks