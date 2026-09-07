"""
Agent 4 — Risk / Constraint Agent.
Proactively scrutinizes requirements, detects edge cases, uncovers hidden assumptions,
and enforces security boundaries.
"""
import json
import logging
from typing import Dict, Any, List

from ai_workflow.agents.base import BaseWorkflowAgent
from ai_workflow.state import WorkflowState, RiskItem
from ai_workflow.prompts.risk_prompts import RISK_SYSTEM_PROMPT, RISK_USER_PROMPT
from ai_workflow.services.llm_factory import LLMFactory

logger = logging.getLogger(__name__)


class RiskAgent(BaseWorkflowAgent):
    """
    Identifies technical risks, domain constraints, and assumption hazards.
    """

    def __init__(self):
        super().__init__(name="risk_constraint_agent")

    async def execute(self, state: WorkflowState) -> Dict[str, Any]:
        provider = LLMFactory.get_provider(role="risk")
        subtasks_data = [t.model_dump() for t in state.subtasks]

        prompt = RISK_USER_PROMPT.format(
            user_input=state.normalized_input or state.user_input,
            subtasks_json=json.dumps(subtasks_data, indent=2),
            tenant_id=state.tenant_id,
            project_id=state.project_id
        )

        raw_output = await provider.generate_async(
            prompt=prompt,
            system_prompt=RISK_SYSTEM_PROMPT,
            temperature=0.3
        )

        risks: List[RiskItem] = []
        constraints: List[str] = [
            f"Strict tenant boundary isolation for tenant '{state.tenant_id}'",
            "Deterministic calculation validity (no arithmetic hallucinations)",
            "Evidence grounding requirement (no fabrication of uncited documents)"
        ]

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
            if isinstance(parsed, list):
                for item in parsed:
                    risks.append(RiskItem(
                        risk_id=item.get("risk_id", f"risk_{len(risks)+1}"),
                        category=item.get("category", "constraint"),
                        description=item.get("description", ""),
                        severity=item.get("severity", "medium")
                    ))
        except Exception as e:
            logger.warning(f"RiskAgent JSON parse fallback ({e}). Using deterministic risk boundaries.")
            risks = [
                RiskItem(risk_id="risk_1", category="security", description="Enforce tenant data isolation boundaries", severity="high"),
                RiskItem(risk_id="risk_2", category="assumption", description="Validate all external inputs before execution", severity="medium")
            ]

        for r in risks:
            constraints.append(f"[{r.category.upper()}] {r.description}")

        logger.info(f"RiskAgent identified {len(risks)} risks and {len(constraints)} active constraints.")
        return {
            "risks": risks,
            "constraints": constraints
        }
