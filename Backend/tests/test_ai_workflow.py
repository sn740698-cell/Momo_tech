"""
Comprehensive Test Suite for MOMO Multi-Agent RAG & Workflow Subsystem.
Covers:
- Workflow state models, schemas, and reducers
- Individual agent execution (Context, Decomp, RAG, Risk, Planner, Solvers, Evaluator)
- LangGraph orchestration, parallel fan-out, synchronized fan-in
- Evaluator structured output and anti-hallucination enforcement
- Conditional retry/feedback loop and exact retry counts (no off-by-one errors)
- Safe unresolved termination upon retry exhaustion
- Strict cross-tenant and cross-project isolation
- Provider abstractions and deterministic mock mode
- Django API endpoints and persistence
"""
import os
import unittest
from unittest.mock import patch
from pydantic import ValidationError

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from ai_workflow.state import (
    WorkflowState,
    EvidenceItem,
    SubTask,
    RiskItem,
    ExecutionPlan,
    EvaluationResult,
    merge_errors,
    merge_evidence
)
from ai_workflow.agents.context_agent import ContextAgent
from ai_workflow.agents.decomposition_agent import DecompositionAgent
from ai_workflow.agents.rag_agent import RAGAgent
from ai_workflow.agents.risk_agent import RiskAgent
from ai_workflow.agents.planning_agent import PlanningAgent
from ai_workflow.agents.solver_primary import PrimarySolverAgent
from ai_workflow.agents.solver_secondary import SecondarySolverAgent
from ai_workflow.agents.evaluator_agent import EvaluatorAgent
from ai_workflow.services.llm_factory import LLMFactory, MockLLMProvider
from ai_workflow.services.embedding_factory import EmbeddingFactory, MockEmbeddingProvider
from ai_workflow.services.retrieval_service import IsolatedRetrievalService
from ai_workflow.services.repository import WorkflowExecutionRepository
from ai_workflow.services.execution_service import ExecutionService
from ai_workflow.graph import ai_workflow_graph, create_ai_workflow_graph


class TestWorkflowStateAndReducers(unittest.TestCase):
    """Verifies state schemas, validation rules, and reducer merge semantics."""

    def test_state_defaults(self):
        state = WorkflowState(user_input="Analyze tenant invoice quarterly summary")
        self.assertTrue(state.execution_id.startswith("exec_"))
        self.assertEqual(state.tenant_id, "default")
        self.assertEqual(state.project_id, "default")
        self.assertEqual(state.retry_count, 0)
        self.assertEqual(state.max_retries, 2)
        self.assertEqual(state.status, "pending")

    def test_evaluation_result_confidence_bounds(self):
        # Valid confidence
        ev = EvaluationResult(is_valid=True, confidence=0.85)
        self.assertEqual(ev.confidence, 0.85)

        # Invalid confidence: > 1.0 must trigger validation error
        with self.assertRaises(ValidationError):
            EvaluationResult(is_valid=True, confidence=1.5)

        # Invalid confidence: < 0.0 must trigger validation error
        with self.assertRaises(ValidationError):
            EvaluationResult(is_valid=True, confidence=-0.2)

    def test_merge_errors_reducer(self):
        e1 = ["Warning: LLM latency elevated"]
        e2 = ["Warning: LLM latency elevated", "Connection timed out"]
        merged = merge_errors(e1, e2)
        self.assertEqual(len(merged), 2)
        self.assertIn("Warning: LLM latency elevated", merged)
        self.assertIn("Connection timed out", merged)

    def test_merge_evidence_reducer(self):
        item1 = EvidenceItem(content="Chunk A", source="doc1", document_id="d1", chunk_index=0)
        item2 = EvidenceItem(content="Chunk B", source="doc1", document_id="d1", chunk_index=1)
        item1_duplicate = EvidenceItem(content="Chunk A duplicate", source="doc1", document_id="d1", chunk_index=0)

        merged = merge_evidence([item1], [item2, item1_duplicate])
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0].content, "Chunk A")
        self.assertEqual(merged[1].content, "Chunk B")


class TestWorkflowAgentsIndividually(unittest.IsolatedAsyncioTestCase):
    """Unit tests for each agent's execution and output formatting."""

    def setUp(self):
        os.environ["AI_MOCK_MODE"] = "true"

    async def test_context_agent_valid(self):
        agent = ContextAgent()
        state = WorkflowState(
            user_input="  Check Q3 payment reconciliation   ",
            tenant_id="tenant_alpha",
            project_id="proj_finance"
        )
        res = await agent.run(state)
        self.assertEqual(res["normalized_input"], "Check Q3 payment reconciliation")
        self.assertEqual(res["tenant_id"], "tenant_alpha")
        self.assertEqual(res["project_id"], "proj_finance")
        self.assertEqual(len(res["errors"]), 0)

    async def test_context_agent_invalid_empty(self):
        agent = ContextAgent()
        state = WorkflowState(user_input="   ")
        res = await agent.run(state)
        self.assertTrue(any("INVALID_REQUEST" in e for e in res["errors"]))

    async def test_decomposition_agent(self):
        agent = DecompositionAgent()
        state = WorkflowState(user_input="Reconcile invoices and compute remaining balances")
        res = await agent.run(state)
        subtasks = res.get("subtasks", [])
        self.assertGreater(len(subtasks), 0)
        self.assertTrue(any(t.needs_retrieval for t in subtasks))

    async def test_rag_agent_empty_context(self):
        agent = RAGAgent()
        # Query for non-existent document in empty tenant
        state = WorkflowState(
            user_input="Fetch non-existent statement #XYZ-99999",
            tenant_id="isolated_tenant_empty",
            project_id="empty_proj"
        )
        res = await agent.run(state)
        self.assertEqual(len(res["retrieved_context"]), 0)
        self.assertTrue(res["no_context_found"])

    async def test_risk_agent(self):
        agent = RiskAgent()
        state = WorkflowState(
            user_input="Execute bulk batch payment transfer without confirmation",
            tenant_id="tenant_fin"
        )
        res = await agent.run(state)
        self.assertIn("risks", res)
        self.assertIn("constraints", res)
        self.assertGreater(len(res["risks"]), 0)

    async def test_planning_agent_with_retry_critique(self):
        agent = PlanningAgent()
        # Simulate retry with previous evaluation critique
        state = WorkflowState(
            user_input="Verify invoice calculation",
            retry_count=1,
            max_retries=2,
            evaluation=EvaluationResult(
                is_valid=False,
                confidence=0.4,
                unsupported_claims=["Assumed 50% discount without coupon"],
                missing_requirements=["Actual invoice record"],
                actionable_critique="Remove ungrounded discount claim."
            )
        )
        res = await agent.run(state)
        plan = res.get("plan")
        self.assertIsNotNone(plan)
        self.assertGreater(len(plan.steps), 0)

    async def test_solvers_independent_outputs(self):
        solver_a = PrimarySolverAgent()
        solver_b = SecondarySolverAgent()
        state = WorkflowState(user_input="Evaluate local GPU allocation")
        res_a = await solver_a.run(state)
        res_b = await solver_b.run(state)

        self.assertIn("solver_a_output", res_a)
        self.assertIn("solver_b_output", res_b)
        self.assertTrue(len(res_a["solver_a_output"]) > 0)
        self.assertTrue(len(res_b["solver_b_output"]) > 0)

    async def test_evaluator_anti_hallucination_guard(self):
        agent = EvaluatorAgent()
        # Solvers claim verified invoice details when no context exists
        state = WorkflowState(
            user_input="Check billing",
            no_context_found=True,
            solver_a_output="I verified from invoice #INV-999 that total is $5,000.",
            solver_b_output="Document confirms payment status is cleared."
        )
        res = await agent.run(state)
        ev: EvaluationResult = res["evaluation"]
        self.assertFalse(ev.is_valid)
        self.assertTrue(any("Anti-hallucination" in f for f in ev.hallucination_findings))


class TestTenantAndProjectIsolation(unittest.TestCase):
    """Verifies that data in Tenant A cannot be retrieved by Tenant B."""

    def setUp(self):
        self.retriever = IsolatedRetrievalService()
        WorkflowExecutionRepository.clear_all()

    def test_strict_cross_tenant_isolation(self):
        # Index document belonging to tenant_alpha / project_finance
        self.retriever.index_document_chunks(
            tenant_id="tenant_alpha",
            project_id="project_finance",
            document_id="doc_alpha_secret",
            chunks=[
                "Confidential: Alpha Financial Statement 2026. Net operating income: $4.2M.",
                "Alpha Corporation internal executive compensation matrix."
            ],
            source="alpha_report.pdf"
        )

        # 1. Tenant Beta queries for "Alpha Financial Statement" -> MUST BE EMPTY
        results_beta = self.retriever.retrieve(
            tenant_id="tenant_beta",
            project_id="project_finance",
            query="Alpha Financial Statement 2026",
            top_k=5,
            similarity_threshold=0.0
        )
        self.assertEqual(len(results_beta), 0, "Cross-tenant data leakage detected!")

        # 2. Tenant Alpha in project_hr queries -> MUST BE EMPTY (project boundary isolation)
        results_alpha_hr = self.retriever.retrieve(
            tenant_id="tenant_alpha",
            project_id="project_hr",
            query="Alpha Financial Statement 2026",
            top_k=5,
            similarity_threshold=0.0
        )
        self.assertEqual(len(results_alpha_hr), 0, "Cross-project data leakage within tenant detected!")

        # 3. Tenant Alpha in project_finance queries -> MUST RETURN DOCUMENT
        results_alpha_fin = self.retriever.retrieve(
            tenant_id="tenant_alpha",
            project_id="project_finance",
            query="Alpha Financial Statement 2026",
            top_k=5,
            similarity_threshold=0.0
        )
        self.assertGreater(len(results_alpha_fin), 0)
        self.assertEqual(results_alpha_fin[0].document_id, "doc_alpha_secret")
        self.assertEqual(results_alpha_fin[0].tenant_id, "tenant_alpha")
        self.assertEqual(results_alpha_fin[0].project_id, "project_finance")


class TestWorkflowGraphOrchestration(unittest.IsolatedAsyncioTestCase):
    """Verifies LangGraph compilation, fan-out/fan-in, and retry loops."""

    def setUp(self):
        os.environ["AI_MOCK_MODE"] = "true"
        WorkflowExecutionRepository.clear_all()

    async def test_full_workflow_success(self):
        res = await ExecutionService.execute_workflow(
            user_input="Analyze system architecture and verify boundary constraints",
            tenant_id="tenant_test",
            project_id="proj_main",
            max_retries=2
        )
        self.assertEqual(res["status"], "completed")
        self.assertTrue(res["evaluation_passed"])
        self.assertGreaterEqual(res["confidence"], 0.8)
        self.assertEqual(res["retries_performed"], 0)
        self.assertEqual(res["iterations_used"], 1)
        self.assertTrue(len(res["solution"]) > 0)
        self.assertGreater(res["subtasks_count"], 0)

    async def test_retry_loop_fail_once_then_pass(self):
        """Simulates evaluation failure on attempt 1, followed by pass on attempt 2."""
        with patch.object(LLMFactory, "get_provider", return_value=MockLLMProvider(scenario="fail_once_then_pass")):
            res = await ExecutionService.execute_workflow(
                user_input="Test retry recovery loop",
                tenant_id="tenant_retry",
                project_id="proj_retry",
                max_retries=2
            )
            self.assertEqual(res["status"], "completed")
            self.assertTrue(res["evaluation_passed"])
            self.assertEqual(res["retries_performed"], 1)
            self.assertEqual(res["iterations_used"], 2)

    async def test_retry_exhaustion_exact_count(self):
        """
        Simulates evaluation failure on all attempts.
        Ensures exact termination after MAX_RETRIES without off-by-one errors.
        """
        max_retries = 2
        with patch.object(LLMFactory, "get_provider", return_value=MockLLMProvider(scenario="always_fail")):
            res = await ExecutionService.execute_workflow(
                user_input="Task that persistently fails validation",
                tenant_id="tenant_exhaust",
                project_id="proj_exhaust",
                max_retries=max_retries
            )
            self.assertEqual(res["status"], "unresolved_exhausted")
            self.assertFalse(res["evaluation_passed"])
            self.assertEqual(res["retries_performed"], max_retries)
            self.assertEqual(res["iterations_used"], max_retries + 1)
            self.assertIn("UNRESOLVED", res["solution"])


class TestWorkflowAPIEndpoints(unittest.TestCase):
    """Tests the Django REST Framework workflow API endpoints."""

    def setUp(self):
        os.environ["AI_MOCK_MODE"] = "true"
        from rest_framework.test import APIClient
        self.client = APIClient()
        WorkflowExecutionRepository.clear_all()

    def test_workflow_execute_endpoint_valid(self):
        payload = {
            "input": "Execute financial reconciliation report",
            "tenant_id": "api_tenant_1",
            "project_id": "api_proj_1",
            "max_retries": 1
        }
        response = self.client.post("/api/workflow/execute/", data=payload, format="json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("execution_id", data)
        self.assertIn("solution", data)
        self.assertEqual(data["tenant_id"], "api_tenant_1")
        self.assertEqual(data["project_id"], "api_proj_1")

    def test_workflow_execute_endpoint_empty_input_400(self):
        payload = {
            "input": "   ",
            "tenant_id": "api_tenant_1"
        }
        response = self.client.post("/api/workflow/execute/", data=payload, format="json")
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["status"], "failed")
        self.assertIn("INVALID_REQUEST", data["error"])

    def test_workflow_executions_list_and_detail(self):
        # 1. Execute a workflow run
        self.client.post("/api/workflow/execute/", data={"input": "List test run", "tenant_id": "tenant_list"}, format="json")

        # 2. List runs
        list_resp = self.client.get("/api/workflow/executions/?tenant_id=tenant_list")
        self.assertEqual(list_resp.status_code, 200)
        list_data = list_resp.json()
        self.assertGreater(list_data["count"], 0)
        exec_id = list_data["executions"][0]["execution_id"]

        # 3. Get detail with matching tenant
        detail_resp = self.client.get(f"/api/workflow/executions/{exec_id}/?tenant_id=tenant_list")
        self.assertEqual(detail_resp.status_code, 200)
        detail_data = detail_resp.json()
        self.assertEqual(detail_data["execution_id"], exec_id)

        # 4. Attempt get detail with wrong tenant -> 404
        wrong_tenant_resp = self.client.get(f"/api/workflow/executions/{exec_id}/?tenant_id=wrong_tenant")
        self.assertEqual(wrong_tenant_resp.status_code, 404)

    def test_workflow_health_endpoint(self):
        response = self.client.get("/api/workflow/health/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["workflow_engine"], "online")
        self.assertTrue(data["langgraph"])
        self.assertTrue(data["mock_mode"])


if __name__ == "__main__":
    unittest.main()
