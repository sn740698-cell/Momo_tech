"""
Agent 1 — Context / Initialization Agent.
Validates input, sanitizes request parameters, establishes tenant/project isolation boundaries,
and initializes retry and evaluation parameters. Never fabricates evidence.
"""
import re
import logging
from typing import Dict, Any

from ai_workflow.agents.base import BaseWorkflowAgent
from ai_workflow.state import WorkflowState
from ai_workflow.services.temporal_service import TemporalService

logger = logging.getLogger(__name__)


class ContextAgent(BaseWorkflowAgent):
    """
    Initializes and validates the workflow environment before decomposition.
    """

    def __init__(self):
        super().__init__(name="context_initialization_agent")

    async def execute(self, state: WorkflowState) -> Dict[str, Any]:
        errors = []

        raw_input = (state.user_input or "").strip()
        if not raw_input:
            errors.append("INVALID_REQUEST: user_input cannot be empty.")

        # Normalize input: collapse excessive whitespace and strip control characters
        normalized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw_input)
        normalized = " ".join(normalized.split())

        # Validate tenant and project boundaries
        tenant_id = (state.tenant_id or "default").strip()
        project_id = (state.project_id or "default").strip()
        user_id = (state.user_id or "default").strip()

        # Reject cross-tenant traversal or path injection attempts
        if any(c in tenant_id or c in project_id for c in ("..", "/", "\\")):
            errors.append("AUTHORIZATION_ERROR: Invalid characters detected in tenant or project boundary identifier.")

        # Deterministically compute temporal anchor and intent
        temporal_analysis = TemporalService.analyze_temporal_intent(normalized or raw_input)
        temporal_anchor = temporal_analysis.get("temporal_anchor", {})
        is_realtime = temporal_analysis.get("is_realtime", False)

        return {
            "normalized_input": normalized,
            "tenant_id": tenant_id,
            "project_id": project_id,
            "user_id": user_id,
            "status": "running",
            "retry_count": state.retry_count or 0,
            "max_retries": state.max_retries if state.max_retries >= 0 else 2,
            "temporal_anchor": temporal_anchor,
            "is_realtime_query": is_realtime,
            "errors": errors
        }
