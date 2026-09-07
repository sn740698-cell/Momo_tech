import json
import logging
from typing import List, Dict, Any, Optional
from django.db.models import Q
from .models import UserPreference, FactMemory, ChatHistory

logger = logging.getLogger(__name__)


class MemoryRepository:
    """
    Data access layer for MOMO persistent memory, user preferences, and chat history.
    """

    # --- Preference Management ---
    @staticmethod
    def get_preference(key: str, default: Any = None) -> Any:
        try:
            pref = UserPreference.objects.get(key=key)
            try:
                return json.loads(pref.value)
            except Exception:
                return pref.value
        except UserPreference.DoesNotExist:
            return default

    @staticmethod
    def set_preference(key: str, value: Any, category: str = "general") -> UserPreference:
        str_val = json.dumps(value) if isinstance(value, (dict, list, bool, int, float)) else str(value)
        pref, _ = UserPreference.objects.update_or_create(
            key=key,
            defaults={"value": str_val, "category": category}
        )
        return pref

    @staticmethod
    def get_all_preferences() -> Dict[str, Any]:
        prefs = {}
        for p in UserPreference.objects.all():
            try:
                prefs[p.key] = json.loads(p.value)
            except Exception:
                prefs[p.key] = p.value
        return prefs

    # --- Fact Memory Management ---
    @staticmethod
    def add_fact(content: str, fact_type: str = "general", confidence: float = 1.0, source: str = "conversation") -> FactMemory:
        # Check if already exists to avoid exact duplicate spam
        existing = FactMemory.objects.filter(content__iexact=content.strip()).first()
        if existing:
            existing.confidence = max(existing.confidence, confidence)
            existing.fact_type = fact_type
            existing.save()
            return existing
        return FactMemory.objects.create(
            content=content.strip(),
            fact_type=fact_type,
            confidence=confidence,
            source=source
        )

    @staticmethod
    def search_facts(query: Optional[str] = None, fact_type: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        qs = FactMemory.objects.all()
        if fact_type:
            qs = qs.filter(fact_type=fact_type)
        if query:
            keywords = query.strip().split()
            q_filter = Q()
            for kw in keywords:
                if len(kw) > 2:
                    q_filter |= Q(content__icontains=kw)
            if q_filter:
                qs = qs.filter(q_filter)
        return [
            {
                "id": f.id,
                "type": f.fact_type,
                "content": f.content,
                "confidence": f.confidence,
                "source": f.source,
                "created_at": f.created_at.isoformat(),
            }
            for f in qs[:limit]
        ]

    @staticmethod
    def save_user_memory(content: str, source: str = "user_explicit") -> FactMemory:
        """Saves an explicit memory designated by the user into the database."""
        clean_content = content.strip()
        existing = FactMemory.objects.filter(content__iexact=clean_content).first()
        if existing:
            existing.fact_type = "user_memory"
            existing.confidence = 1.0
            existing.source = source
            existing.save()
            return existing
        return FactMemory.objects.create(
            content=clean_content,
            fact_type="user_memory",
            confidence=1.0,
            source=source
        )

    @staticmethod
    def get_all_saved_memories(limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves all user-saved memories ordered by most recent first."""
        qs = FactMemory.objects.filter(
            Q(fact_type="user_memory") | Q(source="user_explicit")
        ).order_by("-updated_at")[:limit]
        return [
            {
                "id": f.id,
                "type": f.fact_type,
                "content": f.content,
                "confidence": f.confidence,
                "source": f.source,
                "created_at": f.created_at.isoformat(),
                "updated_at": f.updated_at.isoformat(),
            }
            for f in qs
        ]

    @staticmethod
    def search_saved_memories(query: Optional[str] = None, limit: int = 15) -> List[Dict[str, Any]]:
        """Searches explicit user memories by keyword or retrieves recent ones."""
        qs = FactMemory.objects.filter(
            Q(fact_type="user_memory") | Q(source="user_explicit")
        )
        if query:
            keywords = query.strip().split()
            q_filter = Q()
            for kw in keywords:
                if len(kw) > 2 and kw.lower() not in ["memory", "save", "what", "tell", "show"]:
                    q_filter |= Q(content__icontains=kw)
            if q_filter:
                qs = qs.filter(q_filter)
        qs = qs.order_by("-updated_at")[:limit]
        return [
            {
                "id": f.id,
                "type": f.fact_type,
                "content": f.content,
                "confidence": f.confidence,
                "source": f.source,
                "created_at": f.created_at.isoformat(),
            }
            for f in qs
        ]

    @staticmethod
    def delete_fact(fact_id: int) -> bool:
        deleted, _ = FactMemory.objects.filter(id=fact_id).delete()
        return deleted > 0

    # --- Chat History Management ---
    @staticmethod
    def record_message(
        role: str,
        content: str,
        session_id: str = "default",
        expression: str = "normal",
        animation: str = "none",
        thinking: str = ""
    ) -> ChatHistory:
        return ChatHistory.objects.create(
            session_id=session_id,
            role=role,
            content=content,
            expression=expression,
            animation=animation,
            thinking=thinking,
        )

    @staticmethod
    def get_recent_chat(session_id: str = "default", limit: int = 10) -> List[Dict[str, Any]]:
        messages = ChatHistory.objects.filter(session_id=session_id).order_by('-created_at')[:limit]
        # Return in chronological order
        return [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "expression": m.expression,
                "animation": m.animation,
                "thinking": m.thinking,
                "created_at": m.created_at.isoformat(),
            }
            for m in reversed(list(messages))
        ]

    @staticmethod
    def clear_session_chat(session_id: str = "default") -> int:
        count, _ = ChatHistory.objects.filter(session_id=session_id).delete()
        return count

    # --- Complete Memory Wipe (Privacy Center 1-Click Wipe) ---
    @staticmethod
    def wipe_all_memory() -> Dict[str, int]:
        """
        Permanently deletes all stored facts, preferences, and conversation logs.
        """
        facts_count, _ = FactMemory.objects.all().delete()
        history_count, _ = ChatHistory.objects.all().delete()
        prefs_count, _ = UserPreference.objects.all().delete()
        logger.info(f"Memory wiped: {facts_count} facts, {history_count} messages, {prefs_count} preferences.")
        return {
            "facts_deleted": facts_count,
            "messages_deleted": history_count,
            "preferences_deleted": prefs_count,
        }
