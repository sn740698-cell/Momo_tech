"""
Retrieval Agent for MOMO.
Executes semantic query against ChromaDB using DistilBERT embeddings.
Filters by similarity threshold and ranks relevant context chunks.
"""
import logging
from typing import Dict, Any, List

from graph.state import MomoState, RetrievedChunk
from retrieval.retriever import DocumentRetriever

logger = logging.getLogger(__name__)


class RetrievalAgent:
    """
    Retrieves precise contextual chunks from indexed documents.
    """

    def __init__(self):
        self.retriever = DocumentRetriever()

    async def run(self, state: MomoState) -> Dict[str, Any]:
        last_query = ""
        for m in reversed(state.messages):
            if m.role == "user":
                last_query = m.content
                break

        if not last_query:
            return {"current_agent": "retrieval_agent"}

        # Target specific document if mentioned or in metadata
        target_doc = state.metadata.get("target_document_id")

        raw_chunks = self.retriever.retrieve_context(
            query=last_query,
            top_k=4,
            similarity_threshold=0.55,
            document_id=target_doc
        )

        retrieved = []
        for rc in raw_chunks:
            retrieved.append(RetrievedChunk(
                chunk_id=rc["chunk_id"],
                document_id=rc["document_id"],
                content=rc["content"],
                score=rc["score"],
                page=rc.get("page", 1),
                metadata=rc.get("metadata", {})
            ))

        logger.info(f"RetrievalAgent fetched {len(retrieved)} relevant chunks for query: '{last_query[:40]}...'")
        return {
            "retrieved_context": retrieved,
            "current_agent": "retrieval_agent"
        }
