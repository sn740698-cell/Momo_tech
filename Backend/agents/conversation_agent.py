"""
Conversation Agent for MOMO.
Handles conversational dialogue, humor, emotional persona, and Ollama local LLM execution.
"""
import os
import time
import logging
from typing import Dict, Any, Optional

from graph.state import MomoState, Message, MomoResponse, HardwareCommand, RoutingDecision
from ai.ollama_client import OllamaClient
from ai.model_manager import ModelManager
from ai.prompt_builder import PromptBuilder
from ai.response_parser import ResponseParser
from brain.personality import EXPRESSION_ASCII
from security.permissions import PermissionManager

logger = logging.getLogger(__name__)


class ConversationAgent:
    """
    Executes conversational turn within the LangGraph workflow.
    """

    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self.client = ollama_client or OllamaClient()
        self.model_manager = ModelManager(self.client)

    async def run(self, state: MomoState) -> Dict[str, Any]:
        """
        Executes conversation node. Takes MomoState, invokes Ollama,
        and returns updated state contribution dictionary.
        """
        messages = state.messages
        last_user_msg = ""
        for m in reversed(messages):
            if m.role == "user":
                last_user_msg = m.content
                break

        if not last_user_msg:
            last_user_msg = state.voice_input or "Hello"

        # Build prompt incorporating retrieved memory & context
        active_app = state.user_context.active_app if state.user_context else "Desktop"
        session_mins = state.user_context.session_duration_minutes if state.user_context else 0
        idle_secs = state.user_context.idle_seconds if state.user_context else 0

        # Include retrieved context if available from RetrievalAgent
        context_snippets = []
        if state.retrieved_context:
            for c in state.retrieved_context[:3]:
                context_snippets.append(f"[Document Context]: {c.content}")
        
        # Include financial insights if available from DataAnalyzerAgent
        if state.financial_insights:
            for f in state.financial_insights[:2]:
                context_snippets.append(
                    f"[Verified Invoice {f.invoice_number}]: Total {f.currency} {f.invoice_total}, "
                    f"Paid {f.amount_paid}, Balance Due {f.balance_due}, Due Date {f.due_date}, Status {f.payment_status}"
                )

        combined_context = "\n".join(context_snippets) if context_snippets else None

        # Incorporate LangGraph agent intent understanding & directives
        agent_directive = None
        if state.conversation_context:
            agent_directive = f"[AGENT QUERY UNDERSTANDING & DIRECTIVE]:\n{state.conversation_context}"

        system_prompt = PromptBuilder.build_system_prompt(
            user_name="User",
            memories=[combined_context] if combined_context else [],
            active_app=active_app,
            session_minutes=session_mins,
            idle_seconds=idle_secs,
            custom_instructions=agent_directive
        )

        history = [{"role": m.role, "content": m.content} for m in messages[:-1]]
        chat_msgs = PromptBuilder.assemble_messages(
            current_input=last_user_msg,
            chat_history=history[-6:],
            system_prompt=system_prompt
        )

        # Select active model: prioritize model selected in the UI
        requested_model = state.metadata.get("requested_model") if state.metadata else None
        if requested_model and self.model_manager.is_model_installed(requested_model):
            active_model = requested_model
        else:
            active_model = self.model_manager.get_best_available_model()

        logger.info(f"ConversationAgent invoking local model: '{active_model}'")

        # Call Ollama with 0.35 temperature and 640 predict tokens (enables rich, articulate responses)
        timeout_val = int(os.getenv("OLLAMA_TIMEOUT", "90"))
        llm_result = await self.client.chat(
            messages=chat_msgs,
            model=active_model,
            temperature=0.35,
            timeout_seconds=timeout_val,
            format="json",
            num_predict=640
        )

        if llm_result.get("success"):
            raw_content = llm_result.get("content", "")
            thinking = llm_result.get("thinking", "")
            parsed_response = ResponseParser.parse(raw_content, thinking, active_model)
        else:
            # Graceful degraded response when Ollama is unreachable
            err = str(llm_result.get("error", "Local LLM service unavailable."))
            logger.warning(f"Ollama chat error: {err}")
            if "timed out" in err.lower():
                err_msg = f"My local AI model '{active_model}' took a moment to load into memory. I'm warm and ready now — please try asking your question again!"
            elif "not found" in err.lower():
                err_msg = f"Model '{active_model}' was not found in your local Ollama library. Please select an installed model from the dropdown above."
            else:
                err_msg = "My brain is buffering right now. Ensure Ollama is running on port 11434!"

            parsed_response = MomoResponse(
                message=err_msg,
                expression="confused",
                animation="tilt_left",
                speak=True,
                priority="normal",
                ascii="•_•?",
                model=active_model
            )

        # Build assistant message
        asst_msg = Message(
            role="assistant",
            content=parsed_response.message,
            expression=parsed_response.expression,
            animation=parsed_response.animation,
            thinking=parsed_response.thinking
        )

        # Build validated hardware command for ESP32
        _, hw_cmd, _ = PermissionManager.validate_hardware_command({
            "expression": parsed_response.expression,
            "animation": parsed_response.animation,
            "speak": parsed_response.speak
        })

        hardware_cmd = HardwareCommand(**hw_cmd)

        return {
            "messages": [asst_msg],
            "response": parsed_response,
            "momo_expression": parsed_response.expression,
            "momo_animation": parsed_response.animation,
            "hardware_command": hardware_cmd,
            "current_agent": "conversation_agent"
        }
