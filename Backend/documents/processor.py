"""
Document Processing Pipeline Coordinator.
Coordinates parsing, chunking, BERT analysis, financial extraction,
and vector indexing into ChromaDB.
"""
import uuid
import logging
from typing import Dict, Any, Tuple, Optional

from .parser import DocumentParser
from .chunker import DocumentChunker
from nlp.bert_service import BERTContextAnalyzer
from finance.extractor import FinancialExtractor
from retrieval.chroma_service import ChromaRetrievalService
from graph.state import ProcessedDocument, FinancialInsight

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    End-to-end document processing pipeline.
    """

    def __init__(self):
        self.chroma = ChromaRetrievalService()
        self.bert = BERTContextAnalyzer()

    def process_document(
        self,
        content: bytes,
        filename: str,
        document_id: Optional[str] = None
    ) -> Tuple[ProcessedDocument, Optional[FinancialInsight], Dict[str, Any]]:
        doc_id = document_id or f"doc_{uuid.uuid4().hex[:8]}"
        logger.info(f"Processing document {filename} (ID: {doc_id})...")

        # 1. Text Extraction
        raw_text = DocumentParser.parse_bytes(content, filename)
        if not raw_text.strip():
            logger.warning(f"No text could be extracted from {filename}.")
            doc = ProcessedDocument(
                document_id=doc_id,
                filename=filename,
                text="",
                processing_status="failed"
            )
            return doc, None, {"error": "Empty or unparseable document."}

        # 2. Chunking
        chunks = DocumentChunker.chunk_text(raw_text)

        # 3. Sentence-level BERT contextual analysis
        bert_insights = self.bert.extract_contextual_insights(raw_text)

        # 4. Financial information extraction & deterministic calculation
        financial_data = FinancialExtractor.extract_from_text(raw_text)
        financial_insight = None
        if financial_data:
            financial_data["notes"] = f"Extracted from {filename} with {len(bert_insights)} contextual matches."
            financial_insight = FinancialInsight(**financial_data)

        # 5. ChromaDB Indexing
        meta = {
            "filename": filename,
            "invoice_number": financial_insight.invoice_number if financial_insight else "N/A"
        }
        self.chroma.add_chunks(document_id=doc_id, chunks=chunks, metadata=meta)

        processed_doc = ProcessedDocument(
            document_id=doc_id,
            filename=filename,
            document_type="invoice" if financial_insight and financial_insight.invoice_total > 0 else "text",
            text=raw_text,
            chunks=chunks,
            metadata={
                "chunk_count": len(chunks),
                "bert_matches": len(bert_insights),
                "invoice_number": financial_insight.invoice_number if financial_insight else None,
            },
            embedding_reference=f"chroma://{doc_id}",
            processing_status="completed"
        )

        logger.info(f"Document {filename} processed successfully with {len(chunks)} chunks.")
        return processed_doc, financial_insight, {"bert_insights": bert_insights}
