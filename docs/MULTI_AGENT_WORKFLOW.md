# 🧠 MOMO Multi-Agent RAG & Workflow Subsystem

## 1. Overview

The **MOMO Multi-Agent RAG & Workflow Subsystem** brings production-grade agent orchestration, deterministic anti-hallucination evaluation, strict multi-tenant boundary isolation, and LangGraph-driven execution into the MOMO ecosystem.

Designed to extend MOMO's local-first architecture without disrupting its physical ESP32 companion or financial reasoning capabilities, the subsystem operates as a modular, reusable engine located in `Backend/ai_workflow/`.

---

## 2. Architecture & Flow of Control

```text
               Client / API Request (POST /api/workflow/execute/)
                                      │
                                      ▼
                      AI Workflow Service (ExecutionService)
                                      │
                                      ▼
                          LangGraph Workflow State
                                      │
                                      ▼
                       [Context / Initialization Agent]
                                      │
                                      ▼
                            [Decomposition Agent]
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
          [MOMO RAG / Context Agent]          [Risk / Constraint Agent]
          (Tenant/Project Isolated)            (Edge Cases, Assumptions)
                    │                                   │
                    └─────────────────┬─────────────────┘
                                      ▼
                               [Planning Agent] <───────────────────────────┐
                                      │                                     │
                    ┌─────────────────┴─────────────────┐                   │
                    ▼                                   ▼                   │
           [Primary Solver (A)]               [Secondary Solver (B)]        │
           (Configurable LLM)                 (Configurable LLM)            │
                    │                                   │                   │
                    └─────────────────┬─────────────────┘                   │
                                      ▼                                     │
                           [Evaluator / Judge Agent]                        │
                       (Structured Pydantic Evaluation)                     │
                                      │                                     │
                    ┌─────────────────┴─────────────────┐                   │
                    ▼                                   ▼                   │
            [PASS: is_valid=True]              [FAIL: is_valid=False]       │
                    │                                   │                   │
                    ▼                         ┌─────────┴─────────┐         │
           [Finalize Success]                 ▼                   ▼         │
                    │                  retries < MAX        retries >= MAX  │
                    ▼                         │                   │         │
                   END                        └───────────────────┼─────────┘
                                                                  ▼
                                                        [Finalize Exhausted]
                                                                  │
                                                                  ▼
                                                                 END
```

---

## 3. Modular Agents Specification

The workflow implements 8 specialized agents adhering to the `BaseWorkflowAgent` interface:

| Agent | Responsibility | Key Input | Key Output |
| :--- | :--- | :--- | :--- |
| **1. Context Agent** | Request validation, input normalization, tenant boundary enforcement, initialization. | `user_input`, `tenant_id`, `project_id` | `normalized_input`, initialized state |
| **2. Decomposition Agent** | Breaks request into atomic subtasks with dependency tagging and retrieval flags. | `normalized_input` | `subtasks: List[SubTask]` |
| **3. RAG / Context Agent** | Retrieves context chunks from ChromaDB with strict tenant/project filtering. Emits `NO_RELEVANT_CONTEXT_FOUND` sentinel when absent. | `subtasks`, `tenant_id`, `project_id` | `retrieved_context: List[EvidenceItem]` |
| **4. Risk / Constraint Agent** | Challenges assumptions, identifies security boundaries, detects technical constraints. | `subtasks`, `normalized_input` | `risks: List[RiskItem]`, `constraints` |
| **5. Planning Agent** | Integrates decomposition, grounded evidence, and risks into an ordered execution plan. Ingests evaluator critique during retries. | `subtasks`, `retrieved_context`, `risks`, `critique_history` | `plan: ExecutionPlan` |
| **6. Primary Solver (A)** | Solves the task following the plan and grounded context. Separates facts from assumptions. | `plan`, `retrieved_context`, `constraints` | `solver_a_output: str` |
| **7. Secondary Solver (B)** | Independently reviews and solves the task, challenging assumptions and catching edge cases. | `plan`, `retrieved_context`, `constraints` | `solver_b_output: str` |
| **8. Evaluator / Judge Agent** | Cross-evaluates Solver A and Solver B against evidence. Bounded confidence (`0.0 - 1.0`). Detects hallucinations. | `solver_a_output`, `solver_b_output`, `retrieved_context` | `evaluation: EvaluationResult` |

---

## 4. Anti-Hallucination Policy

1. **Agreement is Not Truth**: Solver A and Solver B agreeing does NOT prove factual accuracy.
2. **Evidence is Ground Truth**: Grounding in retrieved context (`retrieved_context`) takes precedence over parametric LLM memory.
3. **Absence of Evidence**: When no context exists (`no_context_found=True`), solvers and evaluators must explicitly acknowledge uncertainty and must NEVER fabricate document citations, dates, or figures.
4. **Deterministic Guardrail**: If `no_context_found` is true and either solver claims to cite an unretrieved document, the Evaluator automatically fails the run with an explicit anti-hallucination finding.

---

## 5. Tenant and Project Isolation

Every retrieval query, document index, and execution record is strictly partitioned by `tenant_id` and `project_id`.

- **Vector Store Querying**: Chunks are filtered by matching metadata:
  ```python
  if doc_tenant != query_tenant or doc_project != query_project:
      continue  # Rejected
  ```
- **Work History**: Executions for `tenant_a` cannot be retrieved or inspected by `tenant_b`. Cross-tenant retrieval requests return HTTP 404.

---

## 6. Deterministic Mock Mode (`AI_MOCK_MODE=true`)

For offline development, CI/CD, and fast unit testing without external LLM dependencies, MOMO includes a full deterministic mock execution mode:

Set in `.env`:
```ini
AI_MOCK_MODE=true
```

When enabled:
- All agents execute the full LangGraph state machine.
- Parallel fan-out, fan-in merges, evaluator checks, and retry branches run deterministically.
- Requires zero API keys and zero local GPU VRAM.

---

## 7. REST API Endpoints

All endpoints are registered under `/api/workflow/` and discoverable via `/api/`:

### 1. Execute Workflow
- **Method**: `POST /api/workflow/execute/`
- **Request Body**:
  ```json
  {
    "input": "Analyze Q3 invoice reconciliation report",
    "tenant_id": "finance_corp",
    "project_id": "q3_audit",
    "user_id": "auditor_1",
    "max_retries": 2,
    "metadata": {}
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "status": "completed",
    "execution_id": "exec_8f1b2c3d4e5f",
    "tenant_id": "finance_corp",
    "project_id": "q3_audit",
    "evaluation_passed": true,
    "confidence": 0.96,
    "iterations_used": 1,
    "retries_performed": 0,
    "max_retries": 2,
    "solution": "VERIFIED SYNTHESIZED SOLUTION...",
    "sources": [],
    "evaluation": {
      "is_valid": true,
      "confidence": 0.96,
      "hallucination_findings": [],
      "unsupported_claims": [],
      "contradictions": [],
      "missing_requirements": [],
      "actionable_critique": "",
      "synthesized_solution": "..."
    },
    "subtasks_count": 3,
    "risks_identified": [],
    "duration_seconds": 0.45,
    "errors": []
  }
  ```

### 2. List Execution History
- **Method**: `GET /api/workflow/executions/?tenant_id=finance_corp&project_id=q3_audit&limit=20`

### 3. Get Execution Detail
- **Method**: `GET /api/workflow/executions/<execution_id>/?tenant_id=finance_corp`

### 4. Query Grounded Sources
- **Method**: `GET /api/workflow/sources/?query=invoice&tenant_id=finance_corp&project_id=q3_audit`

### 5. Workflow Health
- **Method**: `GET /api/workflow/health/`

---

## 8. Configuration

Add the following to `.env`:

```ini
# Multi-Agent RAG & Workflow Subsystem
AI_MOCK_MODE=false
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:4b
LLM_SOLVER_A_PROVIDER=ollama
LLM_SOLVER_B_PROVIDER=ollama
LLM_EVALUATOR_PROVIDER=ollama
EMBEDDING_PROVIDER=distilbert
MAX_RETRIES=2
AI_WORKFLOW_TIMEOUT=60
```

---

## 9. Running Tests

Run the multi-agent test suite:
```powershell
.\venv\Scripts\python.exe -m unittest tests.test_ai_workflow -v
```

Run the entire MOMO test suite:
```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```
