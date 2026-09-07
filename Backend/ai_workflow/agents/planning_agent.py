"""
Agent 5 — Planning Agent.
Synthesizes subtasks, retrieved context, and risk analysis into an actionable execution plan.
Incorporate evaluator critique during retry cycles to systematically resolve deficiencies.
"""
import json
import logging
from typing import Dict, Any, List

from ai_workflow.agents.base import BaseWorkflowAgent
from ai_workflow.state import WorkflowState, ExecutionPlan
from ai_workflow.prompts.planning_prompts import PLANNING_SYSTEM_PROMPT, PLANNING_USER_PROMPT
from ai_workflow.services.llm_factory import LLMFactory

logger = logging.getLogger(__name__)


class PlanningAgent(BaseWorkflowAgent):
    """
    Constructs and refines the execution plan. Directly ingests Evaluator critique on retries.
    """

    def __init__(self):
        super().__init__(name="planning_agent")

    async def execute(self, state: WorkflowState) -> Dict[str, Any]:
        provider = LLMFactory.get_provider(role="planner")

        # Format evidence
        if state.no_context_found or not state.retrieved_context:
            evidence_summary = "NO_RELEVANT_CONTEXT_FOUND. Solvers must not fabricate sources or ungrounded facts."
        else:
            evidence_summary = "\n".join([
                f"- [Doc: {e.document_id} | Chunk {e.chunk_index} | Source: {e.source} | Score: {e.score}]: {e.content[:200]}"
                for e in state.retrieved_context
            ])

        # Format retry feedback if in a retry loop
        retry_context = ""
        if state.retry_count > 0 and state.evaluation:
            critique = state.evaluation.actionable_critique or "Address unsupported claims and hallucination findings."
            unsupported = ", ".join(state.evaluation.unsupported_claims) or "None noted"
            missing = ", ".join(state.evaluation.missing_requirements) or "None noted"
            retry_context = (
                f"\n=== EVALUATOR REJECTION FEEDBACK (REVISION MANDATORY) ===\n"
                f"Actionable Critique: {critique}\n"
                f"Unsupported Claims to Remove: {unsupported}\n"
                f"Missing Requirements to Address: {missing}\n"
                f"Previous Attempt Rejected. REVISE PLAN ACCORDINGLY.\n"
            )

        prompt = PLANNING_USER_PROMPT.format(
            user_input=state.normalized_input or state.user_input,
            subtasks_json=json.dumps([t.model_dump() for t in state.subtasks], indent=2),
            evidence_summary=evidence_summary,
            risks_json=json.dumps([r.model_dump() for r in state.risks], indent=2),
            retry_count=state.retry_count,
            max_retries=state.max_retries,
            retry_context=retry_context
        )

        raw_output = await provider.generate_async(
            prompt=prompt,
            system_prompt=PLANNING_SYSTEM_PROMPT,
            temperature=0.3
        )

        plan: ExecutionPlan
        try:
            cleaned = raw_output.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()

            parsed = json.loads(cleaned)
            plan = ExecutionPlan(
                steps=parsed.get("steps", []),
                grounding_notes=parsed.get("grounding_notes", ""),
                assumptions=parsed.get("assumptions", []),
                revision_notes=parsed.get("revision_notes")
            )
        except Exception as e:
            logger.warning(f"PlanningAgent JSON parse fallback ({e}). Using deterministic plan.")
            plan = ExecutionPlan(
                steps=[
                    "Validate request requirements against tenant boundary constraints.",
                    "Synthesize facts grounded directly in retrieved project context.",
                    "Formulate verifiable solution without unbacked assumptions."
                ],
                grounding_notes="Grounded in available evidence." if not state.no_context_found else "NO_RELEVANT_CONTEXT_FOUND",
                assumptions=["Operating in local-first environment"],
                revision_notes=state.evaluation.actionable_critique if state.evaluation else None
            )

        logger.info(f"PlanningAgent established plan with {len(plan.steps)} steps (Retry cycle {state.retry_count}).")
        return {"plan": plan}
