"""
Texting Agent for MOMO.
Drafts polite, concise, and professional balance-due notifications and reminders.
Strictly uses validated numbers from state; never invents financial figures.
"""
import logging
from typing import Dict, Any, Optional

from graph.state import MomoState, Message, MomoResponse
from ai.ollama_client import OllamaClient
from ai.model_manager import ModelManager

logger = logging.getLogger(__name__)


class TextingAgent:
    """
    Drafts professional balance-due and reminder messages based on verified financial state.
    """

    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self.client = ollama_client or OllamaClient()
        self.model_manager = ModelManager(self.client)

    async def run(self, state: MomoState) -> Dict[str, Any]:
        insights = state.financial_insights
        recipient = state.metadata.get("recipient_name", "Customer")
        tone = state.metadata.get("draft_tone", "polite and professional")

        if not insights:
            # Fallback draft if no structured invoice in state
            draft = f"Hi {recipient}, this is a gentle reminder regarding your account balance. Please let us know if you need any assistance. Thank you!"
            return {
                "draft_text": draft,
                "response": MomoResponse(
                    message=f"I've drafted a message for {recipient}: \"{draft}\"",
                    expression="happy",
                    animation="nod"
                ),
                "current_agent": "texting_agent"
            }

        primary_insight = insights[0]
        inv_no = primary_insight.invoice_number
        currency = primary_insight.currency
        balance = primary_insight.balance_due
        due_date = primary_insight.due_date or "the due date"
        total = primary_insight.invoice_total

        # Format prompt for local LLM to polish into natural language
        prompt = (
            f"You are MOMO's Texting Agent. Draft a concise, {tone} reminder message.\n"
            f"Customer: {recipient}\n"
            f"Invoice Number: {inv_no}\n"
            f"Total: {currency} {total:,.2f}\n"
            f"Balance Due: {currency} {balance:,.2f}\n"
            f"Due Date: {due_date}\n\n"
            f"Rules:\n"
            f"1. Be concise (2-3 sentences).\n"
            f"2. Use strictly the provided numbers.\n"
            f"3. Do NOT invent payment methods or bank accounts.\n"
            f"4. Do NOT be aggressive.\n"
            f"Return ONLY the draft text, with no introductory banter."
        )

        model = self.model_manager.get_best_available_model()
        llm_res = await self.client.chat(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0.3
        )

        if llm_res.get("success") and llm_res.get("content"):
            draft = llm_res.get("content", "").strip()
            # Clean possible quotes
            if draft.startswith('"') and draft.endswith('"'):
                draft = draft[1:-1].strip()
        else:
            # Deterministic template fallback
            curr_symbol = "₹" if currency == "INR" else ("$" if currency == "USD" else currency)
            draft = (
                f"Hi {recipient}, this is a friendly reminder that {curr_symbol}{balance:,.2f} "
                f"remains due on invoice {inv_no} (due {due_date}). "
                f"Please let us know if you have any questions. Thank you!"
            )

        asst_msg = Message(
            role="assistant",
            content=f"Here is the draft reminder for {recipient}:\n\n> {draft}\n\nYou can review and edit it in the dashboard before sending.",
            expression="proud",
            animation="nod"
        )

        return {
            "draft_text": draft,
            "messages": [asst_msg],
            "response": MomoResponse(
                message=asst_msg.content,
                expression="proud",
                animation="nod"
            ),
            "momo_expression": "proud",
            "momo_animation": "nod",
            "current_agent": "texting_agent"
        }
