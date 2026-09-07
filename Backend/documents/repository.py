"""
Storage repository for uploaded and processed documents.
"""
from typing import Dict, Any, List, Optional
from graph.state import ProcessedDocument, FinancialInsight


class DocumentRepository:
    """
    Repository caching processed documents and financial records.
    """
    _documents: Dict[str, ProcessedDocument] = {}
    _insights: Dict[str, FinancialInsight] = {}

    @classmethod
    def save(cls, doc: ProcessedDocument, insight: Optional[FinancialInsight] = None):
        cls._documents[doc.document_id] = doc
        if insight:
            cls._insights[doc.document_id] = insight

    @classmethod
    def get_document(cls, document_id: str) -> Optional[ProcessedDocument]:
        return cls._documents.get(document_id)

    @classmethod
    def get_insight_by_doc(cls, document_id: str) -> Optional[FinancialInsight]:
        return cls._insights.get(document_id)

    @classmethod
    def get_all_documents(cls) -> List[ProcessedDocument]:
        return list(cls._documents.values())

    @classmethod
    def delete_document(cls, document_id: str) -> bool:
        if document_id in cls._documents:
            del cls._documents[document_id]
            if document_id in cls._insights:
                del cls._insights[document_id]
            return True
        return False

    @classmethod
    def clear_all(cls):
        cls._documents.clear()
        cls._insights.clear()
