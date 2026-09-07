"""
Event Manager for MOMO.
Coordinates inbound telemetry, lifecycle events, and proactive reactions.
"""
import logging
from typing import Optional, Dict, Any

from .schemas import MomoEvent
from .rules import EventRules

logger = logging.getLogger(__name__)


class EventManager:
    """
    Central dispatcher for events occurring across desktop, hardware, and timers.
    """

    @classmethod
    def emit_event(cls, event_type: str, source: str = "system", payload: Optional[Dict[str, Any]] = None) -> MomoEvent:
        event = MomoEvent(
            event_type=event_type,
            source=source,
            payload=payload or {}
        )
        logger.info(f"Event emitted: [{source}] {event_type}")
        return event

    @classmethod
    def evaluate_proactive_reaction(
        cls,
        session_minutes: int,
        idle_seconds: int,
        minutes_since_interaction: float,
        active_app: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        triggered, ev_type, payload = EventRules.evaluate(
            session_minutes=session_minutes,
            idle_seconds=idle_seconds,
            minutes_since_interaction=minutes_since_interaction,
            active_app=active_app
        )
        if triggered and payload:
            return {
                "event_type": ev_type,
                "data": payload
            }
        return None
