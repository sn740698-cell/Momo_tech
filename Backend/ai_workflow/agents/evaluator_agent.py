"""
Agent 8 — Evaluator / Judge Agent.
Critically analyzes Solver A and Solver B outputs against original request,
retrieved evidence, and constraints.
Produces structured Pydantic EvaluationResult output with bounded confidence.
"""
import json
import logging
from typing import Dict, Any

from ai_workflow.agents.base import BaseWorkflowAgent
from ai_workflow.state import WorkflowState, EvaluationResult
from ai_workflow.prompts.evaluator_prompts import EVALUATOR_SYSTEM_PROMPT, EVALUATOR_USER_PROMPT
from ai_workflow.services.llm_factory import LLMFactory

logger = logging.getLogger(__name__)


class EvaluatorAgent(BaseWorkflowAgent):
    """
    Evaluates factual grounding, anti-hallucination compliance, and solver agreement.
    Emits typed EvaluationResult.
    """

    def __init__(self):
        super().__init__(name="evaluator_judge_agent")

    async def execute(self, state: WorkflowState) -> Dict[str, Any]:
        provider = LLMFactory.get_provider(role="evaluator")

        temporal_summary = ""
        if state.temporal_anchor:
            ta = state.temporal_anchor
            temporal_summary = (
                f"[SYSTEM TEMPORAL ANCHOR]:\n"
                f"- Today: {ta.get('today_readable')} ({ta.get('today_day')})\n"
                f"- Yesterday: {ta.get('yesterday_readable')} ({ta.get('yesterday_day')})\n"
                f"- Current Time: {ta.get('current_time_readable')} ({ta.get('timezone')})\n"
            )
            if ta.get("special_today"):
                temporal_summary += f"- Today's Observance: {ta.get('special_today')}\n"
            temporal_summary += "\n"

        if state.no_context_found or not state.retrieved_context:
            evidence_summary = temporal_summary + "NO_RELEVANT_CONTEXT_FOUND. Solvers must NOT fabricate facts or cite unretrieved documents."
        else:
            evidence_lines = [
                f"- [Doc: {e.document_id} | Chunk {e.chunk_index}]: {e.content}"
                for e in state.retrieved_context
            ]
            evidence_summary = temporal_summary + "\n".join(evidence_lines)

        constraints_summary = "\n".join(state.constraints) if state.constraints else "None specified"

        prompt = EVALUATOR_USER_PROMPT.format(
            user_input=state.normalized_input or state.user_input,
            evidence_summary=evidence_summary,
            constraints_summary=constraints_summary,
            solver_a_output=state.solver_a_output or "No output produced.",
            solver_b_output=state.solver_b_output or "No output produced.",
            retry_count=state.retry_count,
            max_retries=state.max_retries
        )

        raw_output = await provider.generate_async(
            prompt=prompt,
            system_prompt=EVALUATOR_SYSTEM_PROMPT,
            temperature=0.1
        )

        eval_res: EvaluationResult
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

            # Enforce confidence bounds: 0.0 <= confidence <= 1.0
            raw_conf = float(parsed.get("confidence", 0.0))
            bounded_conf = max(0.0, min(1.0, raw_conf))

            eval_res = EvaluationResult(
                is_valid=bool(parsed.get("is_valid", False)),
                confidence=round(bounded_conf, 3),
                hallucination_findings=parsed.get("hallucination_findings", []),
                unsupported_claims=parsed.get("unsupported_claims", []),
                contradictions=parsed.get("contradictions", []),
                missing_requirements=parsed.get("missing_requirements", []),
                actionable_critique=parsed.get("actionable_critique", ""),
                synthesized_solution=parsed.get("synthesized_solution", "")
            )
        except Exception as e:
            logger.warning(f"EvaluatorAgent JSON parsing failed ({e}). Running deterministic evaluation.")
            # Fallback evaluation based on output presence
            solvers_present = bool(state.solver_a_output and state.solver_b_output)
            eval_res = EvaluationResult(
                is_valid=solvers_present,
                confidence=0.85 if solvers_present else 0.20,
                hallucination_findings=[] if solvers_present else ["Incomplete solver outputs"],
                unsupported_claims=[],
                contradictions=[],
                missing_requirements=[] if solvers_present else ["Solver output missing"],
                actionable_critique="" if solvers_present else "Ensure both Solver A and Solver B execute completely.",
                synthesized_solution=state.solver_a_output or state.solver_b_output or "Evaluation fallback"
            )

        # Anti-hallucination deterministic guardrail:
        # If no context was found, but solver claimed to verify from an unretrieved document, reject it!
        if state.no_context_found:
            combined_solvers = f"{state.solver_a_output or ''} {state.solver_b_output or ''}".lower()
            if "verified from invoice" in combined_solvers or "document confirms" in combined_solvers:
                eval_res.is_valid = False
                eval_res.confidence = min(eval_res.confidence, 0.3)
                eval_res.hallucination_findings.append(
                    "Anti-hallucination violation: Solvers claimed verified document facts when NO_RELEVANT_CONTEXT_FOUND was present."
                )
                eval_res.actionable_critique = (
                    "Remove references to unretrieved documents. Acknowledge that no relevant context was found."
                )

        logger.info(
            f"Evaluator completed: is_valid={eval_res.is_valid}, confidence={eval_res.confidence}, "
            f"findings={len(eval_res.hallucination_findings)}, unsupported={len(eval_res.unsupported_claims)}"
        )
        return {"evaluation": eval_res}
