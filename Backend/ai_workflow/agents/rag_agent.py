"""
Agent 3 — MOMO RAG / Context Agent.
Executes semantic query against ChromaDB with strict tenant/project boundary isolation.
Never hallucinates sources; explicitly marks NO_RELEVANT_CONTEXT_FOUND when evidence is absent.
"""
import logging
from typing import Dict, Any, List

from ai_workflow.agents.base import BaseWorkflowAgent
from ai_workflow.state import WorkflowState, EvidenceItem
from ai_workflow.services.retrieval_service import IsolatedRetrievalService

logger = logging.getLogger(__name__)


class RAGAgent(BaseWorkflowAgent):
    """
    Retrieves grounded context strictly within tenant and project boundaries.
    """

    def __init__(self):
        super().__init__(name="rag_context_agent")
        self.retrieval_service = IsolatedRetrievalService()

    async def execute(self, state: WorkflowState) -> Dict[str, Any]:
        # Formulate query from subtasks needing retrieval or fallback to normalized input
        retrieval_tasks = [t.description for t in state.subtasks if t.needs_retrieval]
        query = " ".join(retrieval_tasks) if retrieval_tasks else state.normalized_input or state.user_input

        # Target specific document if specified in metadata
        target_doc = state.metadata.get("target_document_id")

        items = self.retrieval_service.retrieve(
            tenant_id=state.tenant_id,
            project_id=state.project_id,
            query=query,
            top_k=4,
            similarity_threshold=0.40,
            filter_document_id=target_doc
        )

        no_context = (len(items) == 0)

        if no_context:
            logger.info("RAGAgent: Zero matching context found. Emitting NO_RELEVANT_CONTEXT_FOUND sentinel.")

        return {
            "retrieved_context": items,
            "no_context_found": no_context
        }
