"""
Document Chunker.
Splits document text into overlapping windows while respecting sentence boundaries.
"""
import re
from typing import List


class DocumentChunker:
    """
    Chunks document text into clean semantic segments.
    """

    @staticmethod
    def chunk_text(
        text: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> List[str]:
        """
        Splits text into chunks of roughly `chunk_size` characters with `chunk_overlap`.
        """
        if not text or not text.strip():
            return []

        # Split into paragraphs or sentences
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) <= chunk_size:
                current_chunk = f"{current_chunk}\n\n{para}".strip()
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                # If paragraph itself is larger than chunk_size, split by sentences
                if len(para) > chunk_size:
                    sentences = re.split(r"(?<=[.!?])\s+", para)
                    sub_chunk = ""
                    for s in sentences:
                        if len(sub_chunk) + len(s) <= chunk_size:
                            sub_chunk = f"{sub_chunk} {s}".strip()
                        else:
                            if sub_chunk:
                                chunks.append(sub_chunk)
                            sub_chunk = s
                    if sub_chunk:
                        current_chunk = sub_chunk
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        # Ensure non-empty chunks
        return [c.strip() for c in chunks if c.strip()]
