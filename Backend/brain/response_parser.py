import json
import re
import logging
from typing import Dict, Any
from .personality import VALID_EXPRESSIONS, VALID_ANIMATIONS, VALID_PRIORITIES

logger = logging.getLogger(__name__)


class ResponseParser:
    """
    Validates, extracts, and sanitizes structured companion responses from LLM generation.
    """

    @classmethod
    def parse(cls, raw_text: str) -> Dict[str, Any]:
        """
        Parses raw text from Ollama into a validated schema dictionary.
        Guarantees returned dict has: message, expression, animation, speak, priority.
        """
        if not raw_text or not raw_text.strip():
            return cls.fallback_response("...")

        cleaned = raw_text.strip()

        # 1. Try parsing directly as JSON
        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                return cls._sanitize_and_validate(data)
        except Exception:
            pass

        # 2. Try extracting from markdown code fences ```json ... ``` or ``` ... ```
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if fence_match:
            try:
                data = json.loads(fence_match.group(1))
                if isinstance(data, dict):
                    return cls._sanitize_and_validate(data)
            except Exception:
                pass

        # 3. Try finding the outermost { ... } block
        brace_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if brace_match:
            try:
                data = json.loads(brace_match.group(1))
                if isinstance(data, dict):
                    return cls._sanitize_and_validate(data)
            except Exception:
                pass

        # 4. Fallback recovery: LLM responded in plain unstructured text
        logger.warning("LLM response was not valid JSON; wrapping in fallback structure.")
        return cls.fallback_response(cleaned)

    @classmethod
    def _sanitize_and_validate(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        # Extract message
        message = str(data.get("message", "")).strip()
        if not message and "response" in data:
            message = str(data.get("response", "")).strip()
        if not message and "text" in data:
            message = str(data.get("text", "")).strip()
        if not message:
            message = "..."

        # Validate expression
        raw_expr = str(data.get("expression", "normal")).lower().strip()
        expression = raw_expr if raw_expr in VALID_EXPRESSIONS else "normal"

        # Validate animation
        raw_anim = str(data.get("animation", "none")).lower().strip()
        animation = raw_anim if raw_anim in VALID_ANIMATIONS else "none"

        # Validate speak
        speak = bool(data.get("speak", True))

        # Validate priority
        raw_prio = str(data.get("priority", "normal")).lower().strip()
        priority = raw_prio if raw_prio in VALID_PRIORITIES else "normal"

        return {
            "message": message,
            "expression": expression,
            "animation": animation,
            "speak": speak,
            "priority": priority,
        }

    @classmethod
    def fallback_response(cls, raw_message: str, expression: str = "normal", animation: str = "none") -> Dict[str, Any]:
        return {
            "message": raw_message.strip() if raw_message else "...",
            "expression": expression if expression in VALID_EXPRESSIONS else "normal",
            "animation": animation if animation in VALID_ANIMATIONS else "none",
            "speak": True,
            "priority": "normal",
        }
