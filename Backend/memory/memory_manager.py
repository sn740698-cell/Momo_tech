import re
import logging
from typing import List, Dict, Any, Optional
from asgiref.sync import sync_to_async
from .repository import MemoryRepository
from .chroma_memory import ChromaMemoryService

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    High-level memory coordinator for MOMO:
    - Dual-layer storage: SQLite persistent database + ChromaDB semantic vector store.
    - Explicit memory saving and retrieval ("save it to my memory").
    - Semantic retrieval of prior chats across sessions.
    - Automatic fact extraction from conversation statements.
    """

    # Simple regex patterns for heuristic fact extraction in local environment
    NAME_PATTERNS = [
        re.compile(r"(?:my name is|call me|i am|i'm)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", re.IGNORECASE),
    ]
    PREFERENCE_PATTERNS = [
        re.compile(r"(?:i like|i love|my favorite\s+\w+\s+is)\s+([^.,!]+)", re.IGNORECASE),
        re.compile(r"(?:i hate|i dislike|i don't like)\s+([^.,!]+)", re.IGNORECASE),
    ]
    PROJECT_PATTERNS = [
        re.compile(r"(?:i am working on|i'm building|my project is)\s+([^.,!]+)", re.IGNORECASE),
    ]

    def __init__(self):
        self.repo = MemoryRepository()
        self.chroma_memory = ChromaMemoryService()

    async def record_and_index_interaction(
        self,
        user_text: str,
        assistant_text: str,
        session_id: str = "default"
    ) -> bool:
        """
        Indexes a completed conversation turn into ChromaDB vector memory for future recall.
        """
        try:
            return await sync_to_async(self.chroma_memory.index_chat_interaction)(
                user_text=user_text,
                assistant_text=assistant_text,
                session_id=session_id
            )
        except Exception as e:
            logger.warning(f"Failed to vector index chat turn: {e}")
            return False

    async def save_explicit_memory(self, memory_text: str) -> Dict[str, Any]:
        """
        Saves an explicit memory to both SQLite database and ChromaDB vector store.
        """
        clean_text = memory_text.strip()
        # 1. Save to SQLite FactMemory
        fact = await sync_to_async(self.repo.save_user_memory)(clean_text, source="user_explicit")
        # 2. Embed and index into ChromaDB
        try:
            await sync_to_async(self.chroma_memory.index_saved_memory)(
                memory_text=clean_text,
                fact_id=fact.id
            )
        except Exception as e:
            logger.warning(f"Failed to vector index explicit memory: {e}")

        return {
            "id": fact.id,
            "content": fact.content,
            "created_at": fact.created_at.isoformat()
        }

    async def recall_saved_memories(self, query: str = "") -> List[str]:
        """
        Retrieves user-saved memories combining SQLite database query and ChromaDB vector search.
        """
        memories = []
        # 1. SQLite database lookup
        db_records = await sync_to_async(self.repo.search_saved_memories)(query=query, limit=10)
        seen_texts = set()
        for r in db_records:
            txt = r["content"].strip()
            if txt and txt not in seen_texts:
                seen_texts.add(txt)
                memories.append(txt)

        # 2. ChromaDB semantic vector search
        if query:
            try:
                vector_records = await sync_to_async(self.chroma_memory.search_saved_memories)(
                    query_text=query,
                    top_k=5
                )
                for vr in vector_records:
                    txt = vr["content"].strip()
                    if txt and txt not in seen_texts:
                        seen_texts.add(txt)
                        memories.append(txt)
            except Exception as e:
                logger.warning(f"Vector search in saved memories failed: {e}")

        return memories

    async def search_past_chat_context(self, query: str, limit: int = 3) -> List[str]:
        """
        Searches ChromaDB vector memory for past conversation turns related to the query.
        """
        if not query.strip():
            return []
        try:
            results = await sync_to_async(self.chroma_memory.search_past_chats)(
                query_text=query,
                top_k=limit,
                similarity_threshold=0.45
            )
            return [r["document"] for r in results]
        except Exception as e:
            logger.warning(f"Vector search in chat history failed: {e}")
            return []

    async def get_relevant_memories(self, query: str = "", limit: int = 5) -> List[str]:
        """
        Retrieves formatted fact strings relevant to the prompt or general key memories.
        """
        facts = await sync_to_async(self.repo.search_facts)(query=query, limit=limit)
        return [f"{f['type'].upper()}: {f['content']}" for f in facts]

    async def get_recent_history(self, session_id: str = "default", limit: int = 8) -> List[Dict[str, str]]:
        """
        Retrieves recent chat history formatted for LLM messages payload.
        """
        history = await sync_to_async(self.repo.get_recent_chat)(session_id=session_id, limit=limit)
        return [{"role": h["role"], "content": h["content"]} for h in history]

    async def extract_and_store_facts(self, user_text: str):
        """
        Analyzes user text and saves high-confidence facts asynchronously without blocking.
        """
        if not user_text:
            return

        text = user_text.strip()

        # Check for user identity / name
        for pat in self.NAME_PATTERNS:
            match = pat.search(text)
            if match:
                name = match.group(1).strip()
                if len(name) > 1 and name.lower() not in ["here", "ready", "fine", "good", "happy", "coding", "testing"]:
                    await sync_to_async(self.repo.add_fact)(
                        content=f"User's name is {name}",
                        fact_type="identity",
                        confidence=0.95
                    )
                    await sync_to_async(self.repo.set_preference)(
                        key="user_name",
                        value=name,
                        category="identity"
                    )

        # Check for project / task info
        for pat in self.PROJECT_PATTERNS:
            match = pat.search(text)
            if match:
                proj = match.group(1).strip()
                if len(proj) > 3:
                    await sync_to_async(self.repo.add_fact)(
                        content=f"User is working on: {proj}",
                        fact_type="project",
                        confidence=0.85
                    )

        # Check for preferences
        for pat in self.PREFERENCE_PATTERNS:
            match = pat.search(text)
            if match:
                pref = match.group(1).strip()
                if len(pref) > 3:
                    await sync_to_async(self.repo.add_fact)(
                        content=f"User preference: {match.group(0).strip()}",
                        fact_type="preference",
                        confidence=0.80
                    )
