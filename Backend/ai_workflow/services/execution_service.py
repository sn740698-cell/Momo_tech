"""
Execution Service for MOMO AI Multi-Agent Workflows.
Coordinates graph execution, state persistence, error classification, telemetry,
and API formatting.
"""
import time
import logging
from typing import Dict, Any, Optional

from ai_workflow.state import WorkflowState
from ai_workflow.graph import ai_workflow_graph
from ai_workflow.services.repository import WorkflowExecutionRepository
from ai_workflow.services.llm_factory import LLMFactory
from ai_workflow.services.embedding_factory import EmbeddingFactory
from retrieval.chroma_service import ChromaRetrievalService

logger = logging.getLogger(__name__)


class ExecutionService:
    """
    Service layer providing unified access to multi-agent workflow execution,
    querying, and health telemetry.
    """

    @classmethod
    async def execute_workflow(
        cls,
        user_input: str,
        tenant_id: str = "default",
        project_id: str = "default",
        user_id: str = "default",
        max_retries: int = 2,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Runs the full LangGraph multi-agent workflow from input to evaluated synthesis.
        Persists run history with strict tenant boundaries.
        """
        start_ts = time.time()
        initial_state = WorkflowState(
            user_input=user_input,
            tenant_id=tenant_id,
            project_id=project_id,
            user_id=user_id,
            max_retries=max_retries,
            metadata=metadata or {},
            start_time=start_ts
        )

        logger.info(
            f"Starting workflow execution '{initial_state.execution_id}' "
            f"for tenant='{tenant_id}', project='{project_id}', user='{user_id}'..."
        )

        try:
            # Execute LangGraph asynchronously
            result_dict = await ai_workflow_graph.ainvoke(initial_state.model_dump())
            final_state = WorkflowState(**result_dict)
            if final_state.duration_seconds <= 0:
                final_state.duration_seconds = round(time.time() - start_ts, 3)

        except Exception as e:
            logger.error(f"Fatal error during workflow execution: {e}", exc_info=True)
            duration = round(time.time() - start_ts, 3)
            final_state = initial_state
            final_state.status = "failed"
            final_state.errors.append(f"WORKFLOW_FAILED: {str(e)}")
            final_state.final_output = f"Execution halted due to internal error: {str(e)}"
            final_state.duration_seconds = duration

        # Persist execution run
        record = WorkflowExecutionRepository.save(final_state)

        # Build clean API response payload conforming to MOMO conventions
        return {
            "status": final_state.status,
            "execution_id": final_state.execution_id,
            "tenant_id": final_state.tenant_id,
            "project_id": final_state.project_id,
            "evaluation_passed": final_state.evaluation.is_valid if final_state.evaluation else False,
            "confidence": final_state.evaluation.confidence if final_state.evaluation else 0.0,
            "iterations_used": final_state.retry_count + 1,
            "retries_performed": final_state.retry_count,
            "max_retries": final_state.max_retries,
            "solution": final_state.final_output or "",
            "sources": [s.model_dump() for s in final_state.retrieved_context],
            "evaluation": final_state.evaluation.model_dump() if final_state.evaluation else {
                "is_valid": False,
                "confidence": 0.0,
                "hallucination_findings": [],
                "unsupported_claims": [],
                "contradictions": [],
                "missing_requirements": [],
                "actionable_critique": "",
                "synthesized_solution": ""
            },
            "subtasks_count": len(final_state.subtasks),
            "risks_identified": [r.model_dump() for r in final_state.risks],
            "duration_seconds": final_state.duration_seconds,
            "errors": final_state.errors
        }

    @classmethod
    def get_execution(
        cls,
        execution_id: str,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        return WorkflowExecutionRepository.get_execution(execution_id, tenant_id, project_id)

    @classmethod
    def list_executions(
        cls,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        return WorkflowExecutionRepository.list_executions(tenant_id, project_id, limit)

    @classmethod
    def check_health(cls) -> Dict[str, Any]:
        """Telemetry check for the AI workflow subsystem."""
        mock_mode = LLMFactory.is_mock_mode()
        return {
            "workflow_engine": "online",
            "langgraph": True,
            "mock_mode": mock_mode,
            "llm_provider": "mock" if mock_mode else "ollama",
            "embedding_provider": "mock" if mock_mode else "distilbert",
            "vector_store": "chromadb",
            "timestamp": time.time()
        }
