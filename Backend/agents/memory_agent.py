"""
Memory & Context Agent for MOMO.
Retrieves historical facts, saves explicit memories, and semantic-indexes conversations in ChromaDB.
"""
import logging
from typing import Dict, Any

from graph.state import MomoState
from security.permissions import PermissionManager
from memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


class MemoryAgent:
    """
    Manages memory retrieval, explicit memory storage/recall, and ChromaDB vector context injection.
    """

    def __init__(self):
        self.memory_manager = MemoryManager()

    async def run(self, state: MomoState) -> Dict[str, Any]:
        if not PermissionManager.is_memory_enabled():
            logger.info("Memory is disabled via privacy controls. Skipping memory retrieval.")
            return {
                "current_agent": "memory_agent"
            }

        last_query = ""
        for m in reversed(state.messages):
            if m.role == "user":
                last_query = m.content
                break

        intent = state.user_intent or ""

        # Case 1: Explicit Save-to-Memory Intent
        if intent == "save_memory":
            payload = ""
            if state.metadata and "memory_payload" in state.metadata:
                payload = state.metadata["memory_payload"]
            if not payload:
                payload = last_query

            try:
                saved_rec = await self.memory_manager.save_explicit_memory(payload)
                logger.info(f"MemoryAgent committed explicit memory to database & vector store: {saved_rec}")
                confirmation_context = (
                    f"[EXPLICIT MEMORY COMMITTED TO DATABASE & VECTOR STORE]:\n"
                    f"Stored Fact: \"{payload}\"\n"
                    f"Database ID: {saved_rec.get('id')}\n\n"
                    f"Directive: Confirm to the user in MOMO's articulate, refined voice (inspired by J.A.R.V.I.S.) "
                    f"that this fact has been safely committed to permanent database memory."
                )
                return {
                    "conversation_context": confirmation_context,
                    "current_agent": "memory_agent"
                }
            except Exception as e:
                logger.error(f"Failed to save explicit memory: {e}")
                return {
                    "conversation_context": f"[MEMORY ERROR]: Could not commit memory: {str(e)}",
                    "current_agent": "memory_agent"
                }

        # Case 2: Explicit Recall-from-Memory Intent
        if intent == "recall_memory":
            query = ""
            if state.metadata and "memory_query" in state.metadata:
                query = state.metadata["memory_query"]

            try:
                recalled_items = await self.memory_manager.recall_saved_memories(query=query)
                if recalled_items:
                    item_lines = "\n".join(f"- {item}" for item in recalled_items)
                    recall_context = (
                        f"[RETRIEVED FROM USER DATABASE MEMORY]:\n"
                        f"{item_lines}\n\n"
                        f"Directive: Present these recalled memories clearly, politely, and articulately to the user in MOMO's refined voice "
                        f"(e.g., 'According to my permanent memory records, you have noted that: ...')."
                    )
                else:
                    recall_context = (
                        f"[RETRIEVED FROM USER DATABASE MEMORY]:\n"
                        f"No saved memories found{' for ' + repr(query) if query else ''}.\n\n"
                        f"Directive: Inform the user in MOMO's articulate, courteous voice that no matching records were found in memory, "
                        f"and offer to save any information whenever they wish."
                    )
                return {
                    "conversation_context": recall_context,
                    "current_agent": "memory_agent"
                }
            except Exception as e:
                logger.error(f"Failed to recall memories: {e}")
                return {
                    "conversation_context": f"[MEMORY ERROR]: Could not retrieve memories: {str(e)}",
                    "current_agent": "memory_agent"
                }

        # Case 3: Follow-up Deepening, Conversational & General Inquiries
        if not last_query:
            return {"current_agent": "memory_agent"}

        context_blocks = []
        if state.conversation_context:
            context_blocks.append(state.conversation_context)

        try:
            # 1. Query ChromaDB vector memory for past conversation turns
            past_chats = await self.memory_manager.search_past_chat_context(query=last_query, limit=2)
            if past_chats:
                context_blocks.append("[RELEVANT PAST CONVERSATIONS FROM VECTOR DB]:\n" + "\n---\n".join(past_chats))

            # 2. Retrieve user facts / preferences from database
            facts = await self.memory_manager.get_relevant_memories(query=last_query, limit=3)
            if facts:
                context_blocks.append("[STORED USER FACTS]:\n" + "\n".join(f"- {f}" for f in facts))

            # 3. Extract heuristic facts in background
            await self.memory_manager.extract_and_store_facts(last_query)
        except Exception as e:
            logger.warning(f"Error querying memory in MemoryAgent: {e}")

        combined = "\n\n".join(context_blocks) if context_blocks else state.conversation_context
        return {
            "conversation_context": combined,
            "current_agent": "memory_agent"
        }
