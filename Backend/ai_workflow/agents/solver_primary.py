"""
Agent 6 — Primary Solver / Worker (Solver A).
Independently solves the task according to the plan and grounded context.
Clearly separates verified evidence from unverified assumptions.
"""
import logging
from typing import Dict, Any

from ai_workflow.agents.base import BaseWorkflowAgent
from ai_workflow.state import WorkflowState
from ai_workflow.prompts.solver_prompts import SOLVER_PRIMARY_SYSTEM_PROMPT, SOLVER_PRIMARY_USER_PROMPT
from ai_workflow.services.llm_factory import LLMFactory

logger = logging.getLogger(__name__)


class PrimarySolverAgent(BaseWorkflowAgent):
    """
    Primary solver producing independent solution A.
    """

    def __init__(self):
        super().__init__(name="primary_solver_agent")

    async def execute(self, state: WorkflowState) -> Dict[str, Any]:
        provider = LLMFactory.get_provider(role="solver_a")

        plan_steps = "\n".join(state.plan.steps) if state.plan else "Direct execution"

        if state.no_context_found or not state.retrieved_context:
            evidence_summary = "NO_RELEVANT_CONTEXT_FOUND. Do not fabricate citations or external facts."
        else:
            evidence_summary = "\n".join([
                f"- [{e.source} | Doc {e.document_id}]: {e.content}"
                for e in state.retrieved_context
            ])

        constraints_summary = "\n".join(state.constraints) if state.constraints else "None specified"

        prompt = SOLVER_PRIMARY_USER_PROMPT.format(
            user_input=state.normalized_input or state.user_input,
            plan_steps=plan_steps,
            evidence_summary=evidence_summary,
            constraints_summary=constraints_summary
        )

        output = await provider.generate_async(
            prompt=prompt,
            system_prompt=SOLVER_PRIMARY_SYSTEM_PROMPT,
            temperature=0.4
        )

        logger.info("PrimarySolverAgent completed execution.")
        return {"solver_a_output": output.strip()}
