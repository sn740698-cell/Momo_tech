"""
Execution History Persistence Layer for MOMO AI Workflow.
Supports Django ORM persistence with automatic in-memory fallback for hermetic testing.
Enforces strict tenant and project filtering on execution queries.
"""
import logging
from typing import Dict, Any, List, Optional
import time

from ai_workflow.state import WorkflowState

logger = logging.getLogger(__name__)


class WorkflowExecutionRepository:
    """
    Persists and queries workflow execution records with isolation boundaries.
    """
    _in_memory_records: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def _state_to_dict(cls, state: WorkflowState) -> Dict[str, Any]:
        """Converts WorkflowState into a serialized execution record."""
        return {
            "execution_id": state.execution_id,
            "tenant_id": state.tenant_id,
            "project_id": state.project_id,
            "user_id": state.user_id,
            "request_input": state.user_input,
            "status": state.status,
            "is_valid": state.evaluation.is_valid if state.evaluation else False,
            "confidence": state.evaluation.confidence if state.evaluation else 0.0,
            "retry_count": state.retry_count,
            "max_retries": state.max_retries,
            "final_output": state.final_output or "",
            "evaluation_result": state.evaluation.model_dump() if state.evaluation else {},
            "retrieved_sources": [item.model_dump() for item in state.retrieved_context],
            "plan": state.plan.model_dump() if state.plan else {},
            "errors": state.errors,
            "duration_seconds": state.duration_seconds,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(state.start_time)),
            "subtasks_count": len(state.subtasks),
            "risks_count": len(state.risks)
        }

    @classmethod
    def save(cls, state: WorkflowState) -> Dict[str, Any]:
        """
        Saves or updates an execution run. Attempts Django ORM, falls back to memory.
        """
        record = cls._state_to_dict(state)
        cls._in_memory_records[state.execution_id] = record

        # Attempt to save to Django ORM if available
        try:
            from momo.models import WorkflowExecution
            WorkflowExecution.objects.update_or_create(
                execution_id=state.execution_id,
                defaults={
                    "tenant_id": state.tenant_id,
                    "project_id": state.project_id,
                    "user_id": state.user_id,
                    "request_input": state.user_input,
                    "status": state.status,
                    "is_valid": record["is_valid"],
                    "confidence": record["confidence"],
                    "retry_count": state.retry_count,
                    "max_retries": state.max_retries,
                    "final_output": record["final_output"],
                    "evaluation_result": record["evaluation_result"],
                    "retrieved_sources": record["retrieved_sources"],
                    "plan": record["plan"],
                    "errors": state.errors,
                    "duration_seconds": state.duration_seconds
                }
            )
            logger.debug(f"Saved execution {state.execution_id} to Django ORM.")
        except Exception as e:
            logger.debug(f"ORM save not active ({e}); execution {state.execution_id} preserved in memory.")

        return record

    @classmethod
    def get_execution(
        cls,
        execution_id: str,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetches an execution by ID, strictly respecting tenant and project boundaries.
        """
        # 1. Check Django ORM
        try:
            from momo.models import WorkflowExecution
            qs = WorkflowExecution.objects.filter(execution_id=execution_id)
            if tenant_id:
                qs = qs.filter(tenant_id=tenant_id)
            if project_id:
                qs = qs.filter(project_id=project_id)
            obj = qs.first()
            if obj:
                return {
                    "execution_id": obj.execution_id,
                    "tenant_id": obj.tenant_id,
                    "project_id": obj.project_id,
                    "user_id": obj.user_id,
                    "request_input": obj.request_input,
                    "status": obj.status,
                    "is_valid": obj.is_valid,
                    "confidence": obj.confidence,
                    "retry_count": obj.retry_count,
                    "max_retries": obj.max_retries,
                    "final_output": obj.final_output,
                    "evaluation_result": obj.evaluation_result,
                    "retrieved_sources": obj.retrieved_sources,
                    "plan": obj.plan,
                    "errors": obj.errors,
                    "duration_seconds": obj.duration_seconds,
                    "created_at": obj.created_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(obj.created_at, "strftime") else str(obj.created_at)
                }
        except Exception:
            pass

        # 2. Check in-memory
        rec = cls._in_memory_records.get(execution_id)
        if rec:
            if tenant_id and rec.get("tenant_id") != tenant_id:
                return None
            if project_id and rec.get("project_id") != project_id:
                return None
            return rec

        return None

    @classmethod
    def list_executions(
        cls,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Lists execution runs filtered by tenant and project.
        """
        try:
            from momo.models import WorkflowExecution
            qs = WorkflowExecution.objects.all()
            if tenant_id:
                qs = qs.filter(tenant_id=tenant_id)
            if project_id:
                qs = qs.filter(project_id=project_id)
            objs = qs[:limit]
            if objs.exists():
                return [
                    {
                        "execution_id": o.execution_id,
                        "tenant_id": o.tenant_id,
                        "project_id": o.project_id,
                        "user_id": o.user_id,
                        "request_input": o.request_input,
                        "status": o.status,
                        "is_valid": o.is_valid,
                        "confidence": o.confidence,
                        "retry_count": o.retry_count,
                        "duration_seconds": o.duration_seconds,
                        "created_at": o.created_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(o.created_at, "strftime") else str(o.created_at)
                    }
                    for o in objs
                ]
        except Exception:
            pass

        # Fallback in-memory
        results = []
        for rec in reversed(list(cls._in_memory_records.values())):
            if tenant_id and rec.get("tenant_id") != tenant_id:
                continue
            if project_id and rec.get("project_id") != project_id:
                continue
            results.append(rec)
            if len(results) >= limit:
                break
        return results

    @classmethod
    def clear_all(cls):
        """Clears in-memory records (used in test suites)."""
        cls._in_memory_records.clear()
        try:
            from momo.models import WorkflowExecution
            WorkflowExecution.objects.all().delete()
        except Exception:
            pass
