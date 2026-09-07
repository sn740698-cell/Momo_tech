"""
LangGraph Multi-Agent Orchestration Graph for MOMO.
Connects Context, Decomposition, RAG, Risk, Planner, Solvers, Evaluator,
and deterministic retry/feedback routing on shared WorkflowState.
"""
import time
import logging
from langgraph.graph import StateGraph, START, END

from ai_workflow.state import WorkflowState
from ai_workflow.agents.context_agent import ContextAgent
from ai_workflow.agents.decomposition_agent import DecompositionAgent
from ai_workflow.agents.rag_agent import RAGAgent
from ai_workflow.agents.web_search_agent import TemporalWebSearchAgent
from ai_workflow.agents.risk_agent import RiskAgent
from ai_workflow.agents.planning_agent import PlanningAgent
from ai_workflow.agents.solver_primary import PrimarySolverAgent
from ai_workflow.agents.solver_secondary import SecondarySolverAgent
from ai_workflow.agents.evaluator_agent import EvaluatorAgent

logger = logging.getLogger(__name__)


# Terminal / State Finalizer Nodes
async def finalize_success_node(state: WorkflowState):
    """Marks execution as successfully completed and verified."""
    duration = round(time.time() - state.start_time, 3)
    sol = state.evaluation.synthesized_solution if state.evaluation else (state.solver_a_output or "")
    logger.info(f"Workflow {state.execution_id} PASSED evaluation in {duration}s.")
    return {
        "status": "completed",
        "final_output": sol,
        "duration_seconds": duration
    }


async def finalize_exhausted_node(state: WorkflowState):
    """Handles exhausted retries safely without false verification claims."""
    duration = round(time.time() - state.start_time, 3)
    sol = state.evaluation.synthesized_solution if state.evaluation else (state.solver_a_output or "")
    exhausted_output = (
        f"[UNRESOLVED: Maximum retries ({state.max_retries}) exhausted without satisfying all verification criteria]\n\n"
        f"Best Available Synthesis:\n{sol}\n\n"
        f"Unresolved Findings:\n"
        f"- Hallucinations/Deficiencies: {', '.join(state.evaluation.hallucination_findings) if state.evaluation else 'None'}\n"
        f"- Unsupported Claims: {', '.join(state.evaluation.unsupported_claims) if state.evaluation else 'None'}\n"
        f"- Actionable Critique: {state.evaluation.actionable_critique if state.evaluation else 'None'}"
    )
    logger.warning(f"Workflow {state.execution_id} exhausted all {state.max_retries} retries without pass.")
    return {
        "status": "unresolved_exhausted",
        "final_output": exhausted_output,
        "duration_seconds": duration
    }


async def finalize_error_node(state: WorkflowState):
    """Terminates workflow early upon fatal initialization or boundary error."""
    duration = round(time.time() - state.start_time, 3)
    err_str = "; ".join(state.errors)
    logger.error(f"Workflow {state.execution_id} aborted with errors: {err_str}")
    return {
        "status": "failed",
        "final_output": f"Workflow execution failed: {err_str}",
        "duration_seconds": duration
    }


async def retry_prep_node(state: WorkflowState):
    """
    Increments retry counter and records evaluator feedback for the Planning Agent.
    Avoids off-by-one errors.
    """
    new_count = state.retry_count + 1
    critique = state.evaluation.actionable_critique if state.evaluation else "Revise solution to eliminate unsupported claims."
    history = list(state.critique_history)
    history.append(f"Retry {new_count}: {critique}")
    logger.info(f"Advancing workflow {state.execution_id} to retry cycle {new_count}/{state.max_retries}...")
    return {
        "retry_count": new_count,
        "critique_history": history
    }


def route_after_context(state: WorkflowState) -> str:
    """Routes to decompose if initialization passed, or error termination if failed."""
    if state.errors:
        return "error"
    return "decompose"


def route_after_evaluator(state: WorkflowState) -> str:
    """
    Evaluates whether the result passes, should retry, or has exhausted retries.
    """
    if state.evaluation and state.evaluation.is_valid:
        return "pass"

    if state.retry_count < state.max_retries:
        return "retry"

    return "exhausted"


def create_ai_workflow_graph():
    """
    Assembles and compiles the MOMO Multi-Agent RAG and Workflow StateGraph.
    Implements clean parallel fan-out and synchronized fan-in merges.
    """
    workflow = StateGraph(WorkflowState)

    # Instantiate agents
    context_agent = ContextAgent()
    decomp_agent = DecompositionAgent()
    rag_agent = RAGAgent()
    web_agent = TemporalWebSearchAgent()
    risk_agent = RiskAgent()
    plan_agent = PlanningAgent()
    solver_a = PrimarySolverAgent()
    solver_b = SecondarySolverAgent()
    evaluator = EvaluatorAgent()

    # Add Agent and Control Nodes
    workflow.add_node("init_context", context_agent.run)
    workflow.add_node("decompose", decomp_agent.run)
    workflow.add_node("retrieve_rag", rag_agent.run)
    workflow.add_node("retrieve_web", web_agent.run)
    workflow.add_node("analyze_risks", risk_agent.run)
    workflow.add_node("plan", plan_agent.run)
    workflow.add_node("solver_primary", solver_a.run)
    workflow.add_node("solver_secondary", solver_b.run)
    workflow.add_node("evaluator", evaluator.run)

    workflow.add_node("retry_prep", retry_prep_node)
    workflow.add_node("finalize_success", finalize_success_node)
    workflow.add_node("finalize_exhausted", finalize_exhausted_node)
    workflow.add_node("finalize_error", finalize_error_node)

    # Edge from START to initialization
    workflow.add_edge(START, "init_context")

    # Conditional check from init
    workflow.add_conditional_edges(
        "init_context",
        route_after_context,
        {
            "decompose": "decompose",
            "error": "finalize_error"
        }
    )

    # Fan-out from Decomposition to RAG, Web Search, and Risk analysis
    workflow.add_edge("decompose", "retrieve_rag")
    workflow.add_edge("decompose", "retrieve_web")
    workflow.add_edge("decompose", "analyze_risks")

    # Fan-in from RAG, Web Search, and Risk to Planner
    workflow.add_edge("retrieve_rag", "plan")
    workflow.add_edge("retrieve_web", "plan")
    workflow.add_edge("analyze_risks", "plan")

    # Fan-out from Planner to Solver A and Solver B
    workflow.add_edge("plan", "solver_primary")
    workflow.add_edge("plan", "solver_secondary")

    # Fan-in from Solvers to Evaluator
    workflow.add_edge("solver_primary", "evaluator")
    workflow.add_edge("solver_secondary", "evaluator")

    # Conditional routing after Evaluator
    workflow.add_conditional_edges(
        "evaluator",
        route_after_evaluator,
        {
            "pass": "finalize_success",
            "retry": "retry_prep",
            "exhausted": "finalize_exhausted"
        }
    )

    # Feedback loop: retry_prep connects back to plan
    workflow.add_edge("retry_prep", "plan")

    # Terminations
    workflow.add_edge("finalize_success", END)
    workflow.add_edge("finalize_exhausted", END)
    workflow.add_edge("finalize_error", END)

    compiled = workflow.compile()
    logger.info("MOMO AI Multi-Agent Workflow StateGraph compiled successfully.")
    return compiled


# Module-level singleton graph
ai_workflow_graph = create_ai_workflow_graph()
