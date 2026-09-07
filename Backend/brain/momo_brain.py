import time
import logging
from typing import Dict, Any, Optional
from asgiref.sync import sync_to_async

from context.context_engine import ContextEngine
from memory.memory_manager import MemoryManager
from memory.repository import MemoryRepository
from ai.ollama_client import OllamaClient
from ai.model_manager import ModelManager
from ai.prompt_builder import PromptBuilder
from .personality import EXPRESSION_ASCII
from .response_parser import ResponseParser
from .decision_engine import DecisionEngine

logger = logging.getLogger(__name__)


class MomoBrain:
    """
    Central brain coordinator for MOMO:
    Connects Context Engine, SQLite Memory, Local LLM (Ollama),
    Response Schema Validation, and Physical Actuation.
    """

    def __init__(self, ollama_host: Optional[str] = None):
        self.context_engine = ContextEngine()
        self.memory_manager = MemoryManager()
        self.memory_repo = MemoryRepository()
        self.decision_engine = DecisionEngine()
        self.ollama_client = OllamaClient(host=ollama_host) if ollama_host else OllamaClient()
        self.model_manager = ModelManager(self.ollama_client)
        self.last_user_interaction_time = time.time()

    async def process_chat(
        self,
        user_message: str,
        session_id: str = "default",
        model: Optional[str] = None,
        use_mock: bool = False
    ) -> Dict[str, Any]:
        """
        Main end-to-end thinking and response generation pipeline.
        """
        self.last_user_interaction_time = time.time()
        self.context_engine.tracker.record_user_action()

        # 1. Save user message in chat history
        await sync_to_async(self.memory_repo.record_message)(
            role="user",
            content=user_message,
            session_id=session_id
        )

        # 2. Extract facts in background
        await self.memory_manager.extract_and_store_facts(user_message)

        # 3. Retrieve user identity, memories, and chat history
        user_name = await sync_to_async(self.memory_repo.get_preference)("user_name", "User")
        memories = await self.memory_manager.get_relevant_memories(query=user_message, limit=5)
        history = await self.memory_manager.get_recent_history(session_id=session_id, limit=6)
        context_snap = self.context_engine.get_snapshot()

        # 4. Handle Mock Brain mode (instant zero-latency fallback)
        if use_mock:
            mock_res = self._generate_mock_response(user_message, user_name)
            await sync_to_async(self.memory_repo.record_message)(
                role="assistant",
                content=mock_res["message"],
                session_id=session_id,
                expression=mock_res["expression"],
                animation=mock_res["animation"]
            )
            return mock_res

        # 5. Build prompt
        system_prompt = PromptBuilder.build_system_prompt(
            user_name=str(user_name),
            memories=memories,
            active_app=context_snap["active_app"],
            session_minutes=context_snap["session_duration_minutes"],
            idle_seconds=context_snap["idle_seconds"]
        )

        messages = PromptBuilder.assemble_messages(
            current_input=user_message,
            chat_history=history[:-1] if history else [],  # exclude just saved message to avoid duplicate
            system_prompt=system_prompt
        )

        active_model = model or self.model_manager.get_best_available_model()

        # 6. Call Ollama Client
        llm_result = await self.ollama_client.chat(
            messages=messages,
            model=active_model,
            temperature=0.7
        )

        thinking_text = ""
        if llm_result.get("success"):
            raw_content = llm_result.get("content", "")
            thinking_text = llm_result.get("thinking", "")
            parsed = ResponseParser.parse(raw_content)
        else:
            # Fallback if Ollama is unreachable or errored
            err_msg = llm_result.get("error", "Local LLM service unavailable.")
            logger.warning(f"Ollama call failed: {err_msg}. Using fallback mock response.")
            parsed = self._generate_fallback_response(user_message, err_msg)

        # 7. Record assistant response in database
        await sync_to_async(self.memory_repo.record_message)(
            role="assistant",
            content=parsed["message"],
            session_id=session_id,
            expression=parsed["expression"],
            animation=parsed["animation"],
            thinking=thinking_text
        )

        return {
            "type": "momo_response",
            "message": parsed["message"],
            "expression": parsed["expression"],
            "animation": parsed["animation"],
            "speak": parsed["speak"],
            "priority": parsed["priority"],
            "ascii": EXPRESSION_ASCII.get(parsed["expression"], "◕ᴗ◕"),
            "thinking": thinking_text,
            "model": active_model,
            "timestamp": time.time(),
        }

    def _generate_mock_response(self, user_text: str, user_name: str) -> Dict[str, Any]:
        """
        Instant zero-latency mock responses for rapid UI testing and fallback.
        """
        lower = user_text.lower()
        if "hello" in lower or "hi" in lower or "hey" in lower:
            return {
                "message": f"Hello {user_name}! I am MOMO, your desktop and robotic companion.",
                "expression": "happy",
                "animation": "wave",
                "speak": True,
                "priority": "normal",
            }
        elif "status" in lower or "health" in lower:
            return {
                "message": "All MOMO systems are operating normally at peak performance!",
                "expression": "excited",
                "animation": "nod",
                "speak": True,
                "priority": "normal",
            }
        elif "sleep" in lower or "night" in lower:
            return {
                "message": "Power saving mode activated. Goodnight! -ᴗ-",
                "expression": "sleepy",
                "animation": "tilt_right",
                "speak": False,
                "priority": "low",
            }
        else:
            return {
                "message": f"I received your message: \"{user_text}\". Ready to assist!",
                "expression": "happy",
                "animation": "nod",
                "speak": True,
                "priority": "normal",
            }

    def _generate_fallback_response(self, user_text: str, error_detail: str) -> Dict[str, Any]:
        """
        Graceful error degradation when Ollama is offline.
        """
        return {
            "message": f"I heard you, but my local LLM daemon is currently offline ({error_detail}). Please ensure Ollama is running on port 11434.",
            "expression": "confused",
            "animation": "tilt_left",
            "speak": True,
            "priority": "normal",
        }

    def check_proactive_rules(self) -> Optional[Dict[str, Any]]:
        """
        Evaluates proactive rules based on live session timer and idle metrics.
        """
        minutes_since_interaction = (time.time() - self.last_user_interaction_time) / 60.0
        snapshot = self.context_engine.get_snapshot()
        
        triggered, event_type, payload = self.decision_engine.evaluate_triggers(
            session_duration_minutes=snapshot["session_duration_minutes"],
            idle_seconds=snapshot["idle_seconds"],
            minutes_since_last_interaction=minutes_since_interaction,
            active_app=snapshot["active_app"]
        )

        if triggered and payload:
            return {
                "type": "momo_response",
                "event_type": event_type,
                "message": payload["message"],
                "expression": payload["expression"],
                "animation": payload["animation"],
                "speak": payload["speak"],
                "priority": payload["priority"],
                "ascii": EXPRESSION_ASCII.get(payload["expression"], "◕ᴗ◕"),
                "timestamp": time.time(),
            }
        return None
