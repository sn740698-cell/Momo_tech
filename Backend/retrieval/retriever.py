"""
High-level document retriever interface.
"""
from typing import List, Dict, Any, Optional
from .chroma_service import ChromaRetrievalService


class DocumentRetriever:
    """
    High-level interface for retrieving context from ingested documents.
    """

    def __init__(self, chroma_service: Optional[ChromaRetrievalService] = None):
        self.chroma = chroma_service or ChromaRetrievalService()

    def retrieve_context(
        self,
        query: str,
        top_k: int = 4,
        similarity_threshold: float = 0.60,
        document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return self.chroma.query(
            query_text=query,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            filter_document_id=document_id
        )
