"""
Automation Agent for MOMO.
Executes desktop tasks (opening websites, browsers, applications, games).
Outputs execution feedback to the state so ConversationAgent and the local LLM
can formulate an articulate, natural confirmation for the user.
"""
import logging
from typing import Dict, Any

from graph.state import MomoState
from automation import get_desktop_controller

logger = logging.getLogger(__name__)


class AutomationAgent:
    """
    Executes desktop and browser automation within the LangGraph workflow.
    """

    def __init__(self):
        self.controller = get_desktop_controller()

    async def run(self, state: MomoState) -> Dict[str, Any]:
        """
        Processes user query for automation intents and executes them.
        """
        last_user_msg = ""
        for m in reversed(state.messages):
            if m.role == "user":
                last_user_msg = m.content
                break

        if not last_user_msg:
            last_user_msg = state.voice_input or ""

        # Detect automation intent
        intent = self.controller.extract_automation_intent(last_user_msg)
        if not intent:
            # Fallback: if user asked "open X", attempt generic web search or URL
            intent = {
                "type": "open_website",
                "target": "requested site",
                "url": f"https://www.google.com/search?q={last_user_msg}",
                "name": last_user_msg
            }

        logger.info(f"AutomationAgent executing intent: {intent}")
        result = self.controller.execute_automation(intent)

        # Build context directive for the LLM
        target_name = result.get("target", "the requested item")
        action_summary = result.get("summary", f"Successfully executed action on {target_name}.")

        directive = (
            f"[DESKTOP AUTOMATION EXECUTED SUCCESSFULLY]\n"
            f"Action: {result.get('action')}\n"
            f"Target: {target_name}\n"
            f"Details: {action_summary}\n"
            f"INSTRUCTION FOR LLM: Confirm cheerfully and articulately to the user that {target_name} has been opened for them."
        )

        metadata_updates = dict(state.metadata)
        metadata_updates["automation_result"] = result

        return {
            "conversation_context": directive,
            "metadata": metadata_updates,
            "current_agent": "automation_agent"
        }
