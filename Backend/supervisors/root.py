"""
Root Supervisor for LangGraph MOMO Workflow.
Directs incoming user intents to the appropriate specialized supervisor:
- conversation: standard dialogue, humor, small talk, questions.
- finance: invoice lookup, balances, calculations, document processing.
- communication: drafting notifications, emails, customer balance reminders.
- voice: speech-to-text / text-to-speech requests.
- system: hardware commands, status diagnostics, settings.
"""
import re
import logging
from typing import Dict, Any

from graph.state import MomoState, RoutingDecision

logger = logging.getLogger(__name__)

FINANCE_KEYWORDS = [
    "invoice", "bill", "due", "balance", "paid", "amount", "rupees", "inr",
    "payment", "receipt", "overdue", "unpaid", "upload", "doc", "document"
]

COMMUNICATION_KEYWORDS = [
    "draft", "message", "remind", "reminder", "email", "sms", "text", "notify",
    "send message", "reach out"
]

SYSTEM_KEYWORDS = [
    "status", "device", "esp32", "robot", "servo", "camera", "privacy", "settings",
    "oled", "led", "telemetry"
]


class RootSupervisor:
    """
    Decides top-level routing branch based on intent analysis.
    """

    @classmethod
    def evaluate_route(cls, text: str, state: MomoState) -> str:
        # Check explicit intent in state metadata first
        if state.metadata.get("target_route"):
            return state.metadata["target_route"]

        # If audio bytes are provided, route to voice
        if state.metadata.get("audio_bytes"):
            return "voice"

        # If upload queue has items, route to finance
        if state.metadata.get("upload_queue"):
            return "finance"

        lower = text.lower()

        # Communication keywords (drafting, texting, notifications)
        if any(w in lower for w in COMMUNICATION_KEYWORDS) and any(w in lower for w in ["reminder", "draft", "invoice", "balance", "customer", "rahul", "client"]):
            return "communication"

        # Finance & Document keywords
        if any(w in lower for w in FINANCE_KEYWORDS):
            return "finance"

        # System & Hardware keywords
        if any(w in lower for w in SYSTEM_KEYWORDS) and any(w in lower for w in ["connect", "servo", "angle", "test", "hardware", "privacy", "reset"]):
            return "system"

        return "conversation"

    @classmethod
    def extract_active_topic(cls, text: str, messages: list) -> str:
        """Extracts the subject of interest from current prompt or prior conversation turns."""
        lower = text.lower()
        # 1. Explicit topic in current message (e.g. 'tell me more about Virat Kohli')
        m = re.search(r"(?:about|on|regarding)\s+([A-Za-z0-9\s]+)", text, re.IGNORECASE)
        if m:
            cand = m.group(1).strip().rstrip("?.!")
            if len(cand) > 1 and cand.lower() not in ["it", "this", "that", "him", "her", "them"]:
                return cand

        # 2. Check prior user questions in conversation turns
        if messages and len(messages) > 1:
            for msg in reversed(messages[:-1]):
                m_text = getattr(msg, "content", "") if hasattr(msg, "content") else msg.get("content", "")
                m_match = re.search(r"(?:who is|what is|tell me about|about)\s+([A-Za-z0-9\s]+)", m_text, re.IGNORECASE)
                if m_match:
                    cand = m_match.group(1).strip().rstrip("?.!")
                    if cand and cand.lower() not in ["it", "this", "that"]:
                        return cand
                if getattr(msg, "role", "") == "user" and 3 <= len(m_text.strip()) <= 40:
                    return m_text.strip().rstrip("?.!")

        return "the previous topic"

    @classmethod
    def safe_eval_math(cls, text: str) -> Optional[str]:
        """Safely evaluates basic arithmetic expressions deterministically."""
        subbed = text.lower()
        subbed = re.sub(r"\bplus\b", "+", subbed)
        subbed = re.sub(r"\bminus\b", "-", subbed)
        subbed = re.sub(r"\btimes\b", "*", subbed)
        subbed = re.sub(r"\bdivided\s+by\b", "/", subbed)
        subbed = re.sub(r"\bdivided\b", "/", subbed)
        subbed = re.sub(r"\bx\b", "*", subbed)
        match = re.search(r"(\d+(?:\.\d+)?(?:\s*[\+\-\*\/]\s*\d+(?:\.\d+)?)+)", subbed)
        if match:
            candidate = match.group(1).strip()
            try:
                code = compile(candidate, "<math>", "eval")
                if not code.co_names:
                    val = eval(code, {"__builtins__": None}, {})
                    if isinstance(val, (int, float)):
                        if isinstance(val, float) and val.is_integer():
                            val = int(val)
                        return str(val)
            except Exception:
                pass
        return None

    @classmethod
    def analyze_query_intent(cls, text: str, messages: Optional[list] = None) -> Dict[str, Any]:
        """
        Deep semantic query understanding across all user inputs.
        Formulates precise directives to guide downstream agents and the LLM.
        """
        lower = text.lower().strip()
        msgs = messages or []

        # 1. Explicit Save-to-Memory command
        save_pattern = re.search(
            r"(?:save(?:\s+it)?\s+to\s+(?:my\s+)?memory|save\s+this\s+(?:in|into|to)\s+(?:my\s+)?memory|remember\s+that|commit\s+to\s+memory)[:\s]*(.*)",
            text,
            re.IGNORECASE
        )
        if save_pattern:
            payload = save_pattern.group(1).strip()
            if not payload:
                # E.g. User said "save this to my memory" referring to previous turn
                prev_turn = msgs[-2].content if len(msgs) >= 2 else ""
                payload = prev_turn.strip()
            return {
                "intent": "save_memory",
                "memory_payload": payload,
                "directive": f"The user explicitly requested to save this to permanent memory: '{payload}'. Confirm politely in MOMO's refined voice that it has been safely committed to database memory."
            }

        # 2. Explicit Recall-from-Memory command
        if any(p in lower for p in [
            "what is in my memory", "what's in my memory", "what did i save in memory",
            "what did i save to my memory", "recall my memory", "show my memory",
            "what do you remember", "check my memory", "retrieve my memory", "my saved memory"
        ]):
            # Extract topic if user asked "what do you remember about X"
            topic_match = re.search(r"(?:about|regarding)\s+([A-Za-z0-9\s]+)", text, re.IGNORECASE)
            search_query = topic_match.group(1).strip().rstrip("?.!") if topic_match else ""
            return {
                "intent": "recall_memory",
                "memory_query": search_query,
                "directive": f"The user is asking to recall information from their saved memory records (query: '{search_query or 'all'}'). Present the stored facts in an articulate, dignified, and organized manner."
            }

        # 3. Conversational Follow-Up / Deepening ('tell me more')
        if any(w in lower for w in [
            "tell me more", "give me more", "more details", "elaborate", "what else",
            "tell me more about", "give me more about", "continue", "go deeper"
        ]):
            topic = cls.extract_active_topic(text, msgs)
            return {
                "intent": "followup_deepening",
                "topic": topic,
                "directive": (
                    f"The user wants deeper, more comprehensive insights regarding '{topic}'. "
                    f"Do NOT repeat the previous introductory response. Deliver a rich, well-explained answer "
                    f"covering specific accomplishments, technical nuances, key milestones, and fascinating insights in MOMO's articulate, J.A.R.V.I.S.-inspired voice."
                )
            }


        # 4. Math / Arithmetic calculation
        has_digits = any(c.isdigit() for c in lower)
        math_ops = ["+", "-", "*", "/", "plus", "minus", "times", "divided", "calculate", "sum of", "product of"]
        if has_digits and any(op in lower for op in math_ops):
            math_ans = cls.safe_eval_math(text)
            if math_ans is not None:
                calc_directive = f"The user is asking for a mathematical calculation. The exact computed result is {math_ans}. State the answer with clear, elegant mathematical phrasing."
            else:
                calc_directive = "The user is asking for a mathematical calculation. Compute the exact result accurately and state the answer with clear, elegant mathematical phrasing."
            return {
                "intent": "calculation",
                "directive": calc_directive
            }

        # 5. Confirmation / Affirmation / Success feedback
        if any(w in lower for w in [
            "yep", "yeah", "yes", "working", "works", "correctly", "fine", "ok", "okay",
            "great", "awesome", "perfect", "good job", "nice", "got it", "understood", "cool"
        ]):
            return {
                "intent": "confirmation",
                "directive": "The user is confirming that everything is working. Reply enthusiastically and politely, like: 'Delighted to hear that. What shall we explore or work on next?'"
            }

        # 6. Identity / Capabilities / System role
        if any(w in lower for w in [
            "who are you", "what are you", "your name", "what can you do",
            "introduce yourself", "tell me about yourself", "how do you work"
        ]):
            return {
                "intent": "identity",
                "directive": "The user is asking about your identity and abilities. Explain with warmth, intelligence, and refined eloquence that you are MOMO, an expressive AI desktop robot companion with an ESP32 physical body."
            }

        # 7. Social greeting / Well-being
        if any(w in lower for w in ["hello", "hi", "hey", "how are you", "how's it going", "good morning", "good evening", "greetings"]):
            return {
                "intent": "greeting",
                "directive": "The user is greeting you or inquiring about your status. Greet them with articulate warmth, and ask how you may assist them today."
            }

        # 8. Financial & Invoices
        if any(w in lower for w in FINANCE_KEYWORDS):
            return {
                "intent": "finance",
                "directive": "The user is asking about financial documents, invoices, balances, or payments. Reference the verified data with precision and clarity."
            }

        # 9. Communication / Reminders
        if any(w in lower for w in COMMUNICATION_KEYWORDS):
            return {
                "intent": "communication",
                "directive": "The user wants to draft a message or reminder. Keep it professional, polished, and effective."
            }

        # 10. Hardware & System
        if any(w in lower for w in SYSTEM_KEYWORDS):
            return {
                "intent": "system",
                "directive": "The user is asking about robot hardware status, servos, OLED screen, or sensors. State technical telemetry clearly."
            }

        # 11. General open-ended knowledge / question
        return {
            "intent": "general_inquiry",
            "directive": "The user is asking a general question or conversational topic. Provide an articulate, well-explained, and easily understood response with depth and elegance."
        }

    async def run(self, state: MomoState) -> Dict[str, Any]:
        last_user_msg = ""
        for m in reversed(state.messages):
            if m.role == "user":
                last_user_msg = m.content
                break

        route = self.evaluate_route(last_user_msg, state)
        intent_info = self.analyze_query_intent(last_user_msg, state.messages)
        directive_text = f"User Intent: {intent_info['intent']}. Directive: {intent_info['directive']}"

        decision = RoutingDecision(
            supervisor="root_supervisor",
            target_agent=f"{route}_supervisor",
            reason=directive_text,
            confidence=0.98
        )

        logger.info(f"RootSupervisor understood intent: '{intent_info['intent']}' -> {route}_supervisor")

        updates: Dict[str, Any] = {
            "current_route": route,
            "user_intent": intent_info["intent"],
            "conversation_context": directive_text,
            "supervisor_decisions": [decision]
        }

        # Store extra intent metadata
        if "memory_payload" in intent_info:
            updates["metadata"] = {**state.metadata, "memory_payload": intent_info["memory_payload"]}
        if "memory_query" in intent_info:
            updates["metadata"] = {**state.metadata, "memory_query": intent_info["memory_query"]}
        if "topic" in intent_info:
            updates["metadata"] = {**state.metadata, "active_topic": intent_info["topic"]}

        return updates
