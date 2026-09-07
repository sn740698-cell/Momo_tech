import json
import re
import logging
from typing import Dict, Any
from .personality import VALID_EXPRESSIONS, VALID_ANIMATIONS, VALID_PRIORITIES

logger = logging.getLogger(__name__)


class ResponseParser:
    """
    Validates, extracts, and sanitizes structured companion responses from LLM generation.
    Guarantees that raw JSON scaffolding and cutoff disclaimers never leak to user.
    """

    CUTOFF_PATTERNS = [
        re.compile(r"as of my (?:current\s+)?knowledge cutoff[^\.\n]*[\.\n]?", re.IGNORECASE),
        re.compile(r"my knowledge cutoff is[^\.\n]*[\.\n]?", re.IGNORECASE),
        re.compile(r"i (?:do not|don't) have (?:access to )?real-time (?:data|information|updates)[^\.\n]*[\.\n]?", re.IGNORECASE),
        re.compile(r"i cannot provide real-time (?:updates|information)[^\.\n]*[\.\n]?", re.IGNORECASE),
        re.compile(r"as an ai (?:language )?model[^\.\n]*[\.\n]?", re.IGNORECASE),
    ]

    @classmethod
    def strip_json_scaffolding(cls, text: str) -> str:
        """
        Extracts human message from raw JSON remnants or strips JSON brackets/keys.
        """
        if not text:
            return ""

        trimmed = text.strip()

        if "{" in trimmed or '"message"' in trimmed or '"expression"' in trimmed or '"animation"' in trimmed:
            msg_match = re.search(r'"message"\s*:\s*"((?:[^"\\]|\\.)*)', trimmed, re.DOTALL)
            if not msg_match:
                msg_match = re.search(r'"(?:content|response|text)"\s*:\s*"((?:[^"\\]|\\.)*)', trimmed, re.DOTALL)

            if msg_match:
                extracted = msg_match.group(1).replace('\\"', '"').replace('\\n', '\n').strip()
                extracted = re.sub(r'["\}]+$', '', extracted).strip()
                if extracted:
                    return extracted

            stripped = re.sub(r'["\']?(?:expression|animation|priority|speak)["\']?\s*:\s*["\']?[^,"\n\}]*["\']?,?', '', trimmed, flags=re.IGNORECASE)
            stripped = re.sub(r'["\']?(?:message|content|response|text)["\']?\s*:\s*"?', '', stripped, flags=re.IGNORECASE)
            stripped = stripped.replace('{', '').replace('}', '').strip()
            stripped = re.sub(r'^["\']|["\']$', '', stripped).strip()
            if stripped:
                return stripped

        return text

    @classmethod
    def sanitize_cutoff_disclaimers(cls, text: str) -> str:
        """Strips artificial AI training cutoff disclaimers."""
        if not text:
            return ""
        sanitized = text
        for pat in cls.CUTOFF_PATTERNS:
            sanitized = pat.sub("", sanitized)
        sanitized = " ".join(sanitized.split()).strip()
        return sanitized

    @classmethod
    def parse(cls, raw_text: str) -> Dict[str, Any]:
        """
        Parses raw text from Ollama into a validated schema dictionary.
        Guarantees returned dict has: message, expression, animation, speak, priority.
        """
        if not raw_text or not raw_text.strip():
            return cls.fallback_response("I am at your service.")

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

        # 3b. Regex recovery for partial/unclosed JSON
        if "{" in cleaned or '"message"' in cleaned:
            msg_match = re.search(r'"message"\s*:\s*"((?:[^"\\]|\\.)*)', cleaned, re.DOTALL)
            if not msg_match:
                msg_match = re.search(r'"(?:content|response|text)"\s*:\s*"((?:[^"\\]|\\.)*)', cleaned, re.DOTALL)

            expr_match = re.search(r'"expression"\s*:\s*"([^"]+)"', cleaned, re.IGNORECASE)
            anim_match = re.search(r'"animation"\s*:\s*"([^"]+)"', cleaned, re.IGNORECASE)

            if msg_match:
                extracted_msg = msg_match.group(1).replace('\\"', '"').replace('\\n', '\n').strip()
                extracted_msg = re.sub(r'["\}]+$', '', extracted_msg).strip()
                return cls._sanitize_and_validate({
                    "message": extracted_msg,
                    "expression": expr_match.group(1) if expr_match else "normal",
                    "animation": anim_match.group(1) if anim_match else "none"
                })

        # 4. Fallback recovery: LLM responded in plain unstructured text
        logger.warning("LLM response was not valid JSON; wrapping in sanitized fallback structure.")
        return cls.fallback_response(cleaned)

    @classmethod
    def _sanitize_and_validate(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        # Extract message
        raw_msg = str(data.get("message", "")).strip()
        if not raw_msg and "response" in data:
            raw_msg = str(data.get("response", "")).strip()
        if not raw_msg and "text" in data:
            raw_msg = str(data.get("text", "")).strip()
        if not raw_msg and "content" in data:
            raw_msg = str(data.get("content", "")).strip()

        # Sanitize message
        clean_msg = cls.strip_json_scaffolding(raw_msg)
        clean_msg = cls.sanitize_cutoff_disclaimers(clean_msg)
        if not clean_msg:
            clean_msg = "I am here and at your service."

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
            "message": clean_msg,
            "expression": expression,
            "animation": animation,
            "speak": speak,
            "priority": priority,
        }

    @classmethod
    def fallback_response(cls, raw_message: str, expression: str = "normal", animation: str = "none") -> Dict[str, Any]:
        cleaned = cls.strip_json_scaffolding(raw_message)
        cleaned = cls.sanitize_cutoff_disclaimers(cleaned)
        if not cleaned or cleaned.strip() in ["{", "}", '""', "...", ""]:
            cleaned = "I am at your service. Please let me know how I can assist you."

        return {
            "message": cleaned,
            "expression": expression if expression in VALID_EXPRESSIONS else "normal",
            "animation": animation if animation in VALID_ANIMATIONS else "none",
            "speak": True,
            "priority": "normal",
        }
