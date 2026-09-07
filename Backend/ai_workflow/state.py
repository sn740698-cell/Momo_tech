"""
Explicit Workflow State Models and Reducers for the MOMO Multi-Agent Subsystem.
Enforces typed schemas, anti-hallucination boundaries, and safe fan-in merges.
"""
from typing import Annotated, List, Dict, Any, Optional
from pydantic import BaseModel, Field
import time
import uuid


def merge_errors(existing: List[str], new_items: List[str]) -> List[str]:
    """Reduces and deduplicates error messages across parallel nodes."""
    merged = list(existing)
    for err in new_items:
        if err not in merged:
            merged.append(err)
    return merged


def merge_evidence(existing: List["EvidenceItem"], new_items: List["EvidenceItem"]) -> List["EvidenceItem"]:
    """Merges evidence items deduplicating by document_id and chunk_index."""
    seen = set()
    result = []
    for item in existing:
        key = (item.document_id, item.chunk_index, item.source)
        if key not in seen:
            seen.add(key)
            result.append(item)
    for item in new_items:
        key = (item.document_id, item.chunk_index, item.source)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


class EvidenceItem(BaseModel):
    """
    Structured retrieved context item preserving source attribution and tenant boundaries.
    Never fabricates similarity scores or source metadata.
    """
    content: str
    source: str = "unknown"
    document_id: str = "unknown"
    chunk_index: int = 0
    page: Optional[int] = 1
    score: float = 0.0
    tenant_id: str = "default"
    project_id: str = "default"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SubTask(BaseModel):
    """
    Atomic task decomposed from the user request.
    """
    task_id: str
    description: str
    needs_retrieval: bool = False
    dependencies: List[str] = Field(default_factory=list)
    status: str = "pending"


class RiskItem(BaseModel):
    """
    Identified technical, security, or domain constraint/risk.
    """
    risk_id: str
    category: str = "constraint"  # 'security', 'assumption', 'constraint', 'failure_mode'
    description: str
    severity: str = "medium"      # 'low', 'medium', 'high', 'critical'


class ExecutionPlan(BaseModel):
    """
    Coherent execution plan integrating decomposition, evidence, and risk analysis.
    """
    steps: List[str] = Field(default_factory=list)
    grounding_notes: str = ""
    assumptions: List[str] = Field(default_factory=list)
    revision_notes: Optional[str] = None


class EvaluationResult(BaseModel):
    """
    Structured evaluation output produced by the Evaluator/Judge agent.
    Confidence is strictly constrained to the range 0.0 - 1.0.
    """
    is_valid: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    hallucination_findings: List[str] = Field(default_factory=list)
    unsupported_claims: List[str] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    missing_requirements: List[str] = Field(default_factory=list)
    actionable_critique: str = ""
    synthesized_solution: str = ""


class WorkflowState(BaseModel):
    """
    Root shared workflow state for the MOMO multi-agent orchestration.
    Maintains tenant/project boundaries, execution history, and parallel branch results.
    """
    execution_id: str = Field(default_factory=lambda: f"exec_{uuid.uuid4().hex[:12]}")
    tenant_id: str = "default"
    project_id: str = "default"
    user_id: str = "default"

    user_input: str = ""
    normalized_input: str = ""

    subtasks: List[SubTask] = Field(default_factory=list)
    retrieved_context: Annotated[List[EvidenceItem], merge_evidence] = Field(default_factory=list)
    no_context_found: bool = False

    risks: List[RiskItem] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)

    plan: Optional[ExecutionPlan] = None

    solver_a_output: Optional[str] = None
    solver_b_output: Optional[str] = None

    evaluation: Optional[EvaluationResult] = None

    retry_count: int = 0
    max_retries: int = 2
    critique_history: List[str] = Field(default_factory=list)

    final_output: Optional[str] = None
    status: str = "pending"  # 'pending', 'running', 'completed', 'unresolved_exhausted', 'failed'

    errors: Annotated[List[str], merge_errors] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    start_time: float = Field(default_factory=time.time)
    duration_seconds: float = 0.0
