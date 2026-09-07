"""
LLM Provider Abstraction and Factory for MOMO AI Workflow.
Supports Ollama (local default), OpenAI-compatible, and deterministic Mock providers.
Fully configurable via environment variables without hardcoded models or secrets.
"""
import os
import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from ai.ollama_client import OllamaClient
from ai.model_manager import ModelManager

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when an invalid provider or model configuration is provided."""
    pass


class LLMProvider(ABC):
    """Abstract interface for all LLM providers in MOMO."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """Synchronously generate text completion from LLM."""
        pass

    async def generate_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """Asynchronously generate completion (defaults to threaded call)."""
        from asgiref.sync import sync_to_async
        return await sync_to_async(self.generate)(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )


class OllamaProvider(LLMProvider):
    """Ollama local model runtime wrapper."""

    def __init__(self, model_name: Optional[str] = None, host: Optional[str] = None):
        self.host = host or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.client = OllamaClient(host=self.host)
        self.model_name = model_name or os.getenv("OLLAMA_MODEL") or ModelManager(self.client).get_best_available_model()

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        messages = [{"role": "user", "content": prompt}]
        res = self.client.chat_sync(
            messages=messages,
            model=self.model_name,
            temperature=temperature,
            system_prompt=system_prompt,
            timeout_seconds=int(os.getenv("AI_WORKFLOW_TIMEOUT", "60"))
        )
        if not res.get("success", False):
            err_msg = res.get("error", "Unknown Ollama error")
            logger.error(f"Ollama generation failed: {err_msg}")
            raise RuntimeError(f"LLM_PROVIDER_ERROR: Ollama failed ({err_msg})")
        return res.get("content", "")


class OpenAICompatibleProvider(LLMProvider):
    """Generic OpenAI-compatible API provider (supports vLLM, LMStudio, OpenAI)."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        import requests
        self.requests = requests
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        try:
            resp = self.requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=int(os.getenv("AI_WORKFLOW_TIMEOUT", "60"))
            )
            if resp.status_code != 200:
                raise RuntimeError(f"LLM_PROVIDER_ERROR: HTTP {resp.status_code} - {resp.text[:200]}")
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"OpenAICompatibleProvider error: {e}")
            raise RuntimeError(f"LLM_PROVIDER_ERROR: {str(e)}")


class MockLLMProvider(LLMProvider):
    """
    Deterministic Mock Provider for testing and hermetic offline execution.
    Generates typed JSON outputs simulating Decomposition, Risks, Planning, Solvers, and Evaluator.
    Supports retry simulation scenarios.
    """

    def __init__(self, scenario: str = "auto"):
        self.scenario = scenario  # 'auto', 'always_pass', 'fail_once_then_pass', 'always_fail'
        self.call_count = 0

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        self.call_count += 1
        sys_lower = (system_prompt or "").lower()
        prompt_lower = prompt.lower()
        combined = f"{sys_lower} {prompt_lower}"

        # 1. Evaluator / Judge Agent (Checked first so 'solver a' inside evaluator prompt doesn't misclassify!)
        if "evaluator / judge agent" in sys_lower or "evaluate both solutions" in prompt_lower:
            # Check for simulated failure scenarios
            is_retry = "retry count: 1" in prompt_lower or "retry count: 2" in prompt_lower

            if self.scenario == "always_fail":
                return json.dumps({
                    "is_valid": False,
                    "confidence": 0.40,
                    "hallucination_findings": ["Unverified citation detected in output"],
                    "unsupported_claims": ["Claimed external API availability without supporting context"],
                    "contradictions": [],
                    "missing_requirements": ["Missing explicit failure fallback mechanism"],
                    "actionable_critique": "Remove ungrounded assumptions regarding external services.",
                    "synthesized_solution": "Best available partial solution (unresolved due to missing evidence)."
                })

            if self.scenario == "fail_once_then_pass":
                if not is_retry:
                    return json.dumps({
                        "is_valid": False,
                        "confidence": 0.45,
                        "hallucination_findings": ["Initial draft contains unsupported assumption"],
                        "unsupported_claims": ["Assumed unlimited memory bandwidth"],
                        "contradictions": [],
                        "missing_requirements": ["Explicit low-VRAM boundary checks"],
                        "actionable_critique": "Revise plan to explicitly enforce 4GB VRAM constraint.",
                        "synthesized_solution": "Intermediate draft requiring refinement."
                    })
                else:
                    return json.dumps({
                        "is_valid": True,
                        "confidence": 0.94,
                        "hallucination_findings": [],
                        "unsupported_claims": [],
                        "contradictions": [],
                        "missing_requirements": [],
                        "actionable_critique": "",
                        "synthesized_solution": "VERIFIED SOLUTION: The revised plan strictly incorporates 4GB VRAM boundaries and deterministic calculation safeguards. Verified across both solvers."
                    })

            # Default / auto / always_pass:
            return json.dumps({
                "is_valid": True,
                "confidence": 0.96,
                "hallucination_findings": [],
                "unsupported_claims": [],
                "contradictions": [],
                "missing_requirements": [],
                "actionable_critique": "",
                "synthesized_solution": "VERIFIED SYNTHESIZED SOLUTION: Both solvers independently reached grounded conclusions consistent with verified evidence and security constraints."
            })

        # 2. Decomposition Agent
        if "decomposition agent" in sys_lower or "atomic subtasks" in prompt_lower:
            return json.dumps([
                {"task_id": "task_1", "description": "Validate request scope and tenant boundaries", "needs_retrieval": False, "dependencies": []},
                {"task_id": "task_2", "description": "Retrieve project documentation and relevant context", "needs_retrieval": True, "dependencies": ["task_1"]},
                {"task_id": "task_3", "description": "Synthesize verified findings and formulate implementation steps", "needs_retrieval": False, "dependencies": ["task_2"]}
            ])

        # 3. Risk / Constraint Agent
        if "risk / constraint agent" in sys_lower or "risks, constraints, and failure modes" in prompt_lower:
            return json.dumps([
                {"risk_id": "risk_1", "category": "security", "description": "Ensure strict tenant boundary enforcement across data queries", "severity": "high"},
                {"risk_id": "risk_2", "category": "constraint", "description": "Adhere strictly to deterministic calculations without LLM fabrication", "severity": "medium"},
                {"risk_id": "risk_3", "category": "assumption", "description": "Verify external dependencies before assuming service availability", "severity": "low"}
            ])

        # 4. Planning Agent
        if "planning agent" in sys_lower or "produce the execution plan" in prompt_lower:
            is_retry = "retry attempt: 1" in prompt_lower or "retry attempt: 2" in prompt_lower or "critique" in prompt_lower
            revision = "Addressed evaluator critique by removing ungrounded claims and anchoring to retrieved evidence." if is_retry else None
            return json.dumps({
                "steps": [
                    "Step 1: Ingest verified tenant evidence and cross-check constraints.",
                    "Step 2: Formulate solution strictly adhering to identified facts.",
                    "Step 3: Document unverified assumptions explicitly."
                ],
                "grounding_notes": "All steps anchored in retrieved project documents.",
                "assumptions": ["System runtime operates in low-latency local environment"],
                "revision_notes": revision
            })

        # 5. Solver Primary (A)
        if "solver a" in sys_lower or "primary solver" in sys_lower:
            return "SOLVER A PRIMARY SOLUTION:\n1. Analysis: Grounded in tenant project records.\n2. Proposed Resolution: Implement deterministic processing pipeline with verified boundaries.\n3. Facts: Retained from document metadata. No assumptions made regarding unprovided data."

        # 6. Solver Secondary (B)
        if "solver b" in sys_lower or "secondary solver" in sys_lower:
            return "SOLVER B INDEPENDENT REVIEW & SOLUTION:\n1. Critical Assessment: Solver A's approach is structurally sound.\n2. Risk Check: Verified zero cross-tenant leakage and strict arithmetic correctness.\n3. Alternative Consideration: Add deterministic boundary validation at query entry."

        # Generic default
        return "Deterministic response from MockLLMProvider."


class LLMFactory:
    """Factory creating configured LLM provider instances for agents."""

    @staticmethod
    def is_mock_mode() -> bool:
        mock_env = os.getenv("AI_MOCK_MODE", "").lower()
        return mock_env in ("true", "1", "yes")

    @classmethod
    def get_provider(cls, role: str = "default", scenario: str = "auto") -> LLMProvider:
        """
        Returns an LLMProvider based on role-specific and global environment configuration.
        Roles: 'default', 'solver_a', 'solver_b', 'evaluator', 'decomposition', 'planner'.
        """
        if cls.is_mock_mode():
            logger.info(f"Using MockLLMProvider for role '{role}' (AI_MOCK_MODE enabled).")
            return MockLLMProvider(scenario=scenario)

        # Check role-specific provider then fallback to general
        role_prefix = f"LLM_{role.upper()}_"
        provider_type = os.getenv(f"{role_prefix}PROVIDER") or os.getenv("LLM_PROVIDER", "ollama").lower()
        model_name = os.getenv(f"{role_prefix}MODEL") or os.getenv("LLM_MODEL")

        if provider_type == "ollama":
            return OllamaProvider(model_name=model_name)
        elif provider_type in ("openai", "openai_compatible"):
            return OpenAICompatibleProvider(model=model_name)
        elif provider_type == "mock":
            return MockLLMProvider(scenario=scenario)
        else:
            raise ConfigurationError(
                f"Unsupported LLM provider '{provider_type}' for role '{role}'. "
                f"Supported providers: 'ollama', 'openai', 'mock'."
            )
