"""
Document Processing Agent for MOMO.
Coordinates text extraction, chunking, and ChromaDB indexing.
"""
import logging
from typing import Dict, Any

from graph.state import MomoState
from documents.processor import DocumentProcessor

logger = logging.getLogger(__name__)


class DocumentAgent:
    """
    Ingests and processes raw documents into structured document chunks.
    """

    def __init__(self):
        self.processor = DocumentProcessor()

    async def run(self, state: MomoState) -> Dict[str, Any]:
        # If pending raw documents exist in metadata, process them
        raw_docs = state.metadata.get("upload_queue", [])
        new_docs = []
        new_insights = []

        for item in raw_docs:
            content = item.get("content", b"")
            filename = item.get("filename", "document.txt")
            doc, insight, _ = self.processor.process_document(content, filename)
            new_docs.append(doc)
            if insight:
                new_insights.append(insight)

        return {
            "documents": new_docs,
            "financial_insights": new_insights,
            "current_agent": "document_agent"
        }
