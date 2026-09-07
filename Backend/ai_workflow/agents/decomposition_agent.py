"""
Agent 2 — Decomposition Agent.
Decomposes complex user requests into atomic, dependency-aware subtasks
and determines retrieval requirements.
"""
import json
import logging
from typing import Dict, Any, List

from ai_workflow.agents.base import BaseWorkflowAgent
from ai_workflow.state import WorkflowState, SubTask
from ai_workflow.prompts.decomposition_prompts import DECOMPOSITION_SYSTEM_PROMPT, DECOMPOSITION_USER_PROMPT
from ai_workflow.services.llm_factory import LLMFactory

logger = logging.getLogger(__name__)


class DecompositionAgent(BaseWorkflowAgent):
    """
    Decomposes the normalized user request into structured SubTasks.
    """

    def __init__(self):
        super().__init__(name="decomposition_agent")

    async def execute(self, state: WorkflowState) -> Dict[str, Any]:
        if state.errors and any("INVALID_REQUEST" in e for e in state.errors):
            return {}

        provider = LLMFactory.get_provider(role="decomposition")
        prompt = DECOMPOSITION_USER_PROMPT.format(
            user_input=state.normalized_input or state.user_input,
            tenant_id=state.tenant_id,
            project_id=state.project_id
        )

        raw_output = await provider.generate_async(
            prompt=prompt,
            system_prompt=DECOMPOSITION_SYSTEM_PROMPT,
            temperature=0.2
        )

        subtasks: List[SubTask] = []
        try:
            # Clean possible markdown fences
            cleaned = raw_output.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()

            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                for item in parsed:
                    subtasks.append(SubTask(
                        task_id=item.get("task_id", f"task_{len(subtasks)+1}"),
                        description=item.get("description", ""),
                        needs_retrieval=bool(item.get("needs_retrieval", False)),
                        dependencies=item.get("dependencies", [])
                    ))
        except Exception as e:
            logger.warning(f"Failed to parse decomposition JSON ({e}); using deterministic fallback.")
            subtasks = [
                SubTask(task_id="task_1", description="Understand and validate requirements", needs_retrieval=False),
                SubTask(task_id="task_2", description="Retrieve grounded contextual information", needs_retrieval=True, dependencies=["task_1"]),
                SubTask(task_id="task_3", description="Execute solution plan", needs_retrieval=False, dependencies=["task_2"])
            ]

        logger.info(f"DecompositionAgent produced {len(subtasks)} atomic subtasks.")
        return {"subtasks": subtasks}
