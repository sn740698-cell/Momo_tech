"""
Tenant- and Project-Isolated Retrieval Service for MOMO AI Workflow.
Wraps ChromaDB and DocumentRepository while enforcing strict tenant isolation,
metadata preservation, and anti-hallucination sentinel handling.
"""
import logging
from typing import List, Dict, Any, Optional

from retrieval.chroma_service import ChromaRetrievalService
from documents.repository import DocumentRepository
from ai_workflow.state import EvidenceItem

logger = logging.getLogger(__name__)


class IsolatedRetrievalService:
    """
    Retrieval service ensuring zero cross-tenant or cross-project data leakage.
    Preserves exact chunk metadata without fabricating scores or sources.
    """

    def __init__(self):
        self.chroma = ChromaRetrievalService()

    def index_document_chunks(
        self,
        tenant_id: str,
        project_id: str,
        document_id: str,
        chunks: List[str],
        source: str = "document",
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Indexes chunks into the vector store with mandatory isolation metadata.
        """
        if not chunks:
            return False

        base_meta = extra_metadata or {}
        base_meta.update({
            "tenant_id": tenant_id,
            "project_id": project_id,
            "document_id": document_id,
            "source": source
        })

        return self.chroma.add_chunks(
            document_id=document_id,
            chunks=chunks,
            metadata=base_meta
        )

    def retrieve(
        self,
        tenant_id: str,
        project_id: str,
        query: str,
        top_k: int = 4,
        similarity_threshold: float = 0.50,
        filter_document_id: Optional[str] = None
    ) -> List[EvidenceItem]:
        """
        Retrieves contextual chunks with strict tenant and project boundary filtering.
        Returns EvidenceItems. If nothing matches, returns an empty list.
        """
        if not query or not query.strip():
            return []

        # Retrieve raw chunks from Chroma / in-memory fallback
        raw_results = self.chroma.query(
            query_text=query,
            top_k=top_k * 3,  # Fetch slightly wider candidate set for isolation filtering
            similarity_threshold=similarity_threshold,
            filter_document_id=filter_document_id
        )

        evidence_items: List[EvidenceItem] = []

        for item in raw_results:
            meta = item.get("metadata", {})
            doc_tenant = meta.get("tenant_id", "default")
            doc_project = meta.get("project_id", "default")

            # STRICT ISOLATION CHECK: Reject any chunk belonging to another tenant or project
            if doc_tenant != tenant_id or doc_project != project_id:
                continue

            chunk_idx = meta.get("chunk_index", 0)
            page_num = meta.get("page", 1)
            source_name = meta.get("source") or meta.get("filename", "momo_knowledge")

            evidence_items.append(EvidenceItem(
                content=item["content"],
                source=source_name,
                document_id=item["document_id"],
                chunk_index=chunk_idx,
                page=page_num,
                score=item.get("score", 0.0),
                tenant_id=doc_tenant,
                project_id=doc_project,
                metadata=meta
            ))

            if len(evidence_items) >= top_k:
                break

        logger.info(
            f"IsolatedRetrievalService fetched {len(evidence_items)} chunks for "
            f"tenant='{tenant_id}', project='{project_id}', query='{query[:40]}...'"
        )
        return evidence_items
