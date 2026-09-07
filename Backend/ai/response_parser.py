"""
Robust JSON and structured output parser for LLM responses.
Handles raw markdown codeblocks, malformed JSON, and ensures fallback safety.
"""
import json
import re
import logging
from typing import Dict, Any, Optional

from graph.state import MomoResponse
from brain.personality import (
    VALID_EXPRESSIONS,
    VALID_ANIMATIONS,
    VALID_PRIORITIES,
    EXPRESSION_ASCII,
)

logger = logging.getLogger(__name__)


class ResponseParser:
    """
    Parses LLM generation text into strict MomoResponse schemas.
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
        If text contains raw JSON remnants (e.g. from partial generation or malformed syntax),
        extracts the human message value or strips the JSON scaffolding so raw JSON never leaks to chat.
        """
        if not text:
            return ""

        trimmed = text.strip()

        # Check if text contains JSON-like structures or keys
        if "{" in trimmed or '"message"' in trimmed or '"expression"' in trimmed or '"animation"' in trimmed:
            # Try to regex extract content of "message" field even from truncated or unclosed JSON
            msg_match = re.search(r'"message"\s*:\s*"((?:[^"\\]|\\.)*)', trimmed, re.DOTALL)
            if not msg_match:
                msg_match = re.search(r'"(?:content|response|text)"\s*:\s*"((?:[^"\\]|\\.)*)', trimmed, re.DOTALL)

            if msg_match:
                extracted = msg_match.group(1)
                # Unescape common escaped characters
                extracted = extracted.replace('\\"', '"').replace('\\n', '\n').replace('\\t', ' ')
                # Remove any trailing unclosed quote or brace remnants
                extracted = re.sub(r'["\}]+$', '', extracted).strip()
                if extracted:
                    return extracted

            # If no "message": "..." match succeeded, strip all JSON key-value pairs, brackets, and braces
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
    def clean_text(cls, text: str) -> str:
        """Strips roleplay prefixes, JSON scaffolding, cutoff excuses, and echoes."""
        if not text:
            return ""

        # First, strip JSON keys/brackets if raw JSON leaked into text
        cleaned = cls.strip_json_scaffolding(text)
        cleaned = cleaned.strip()

        # Strip speaker labels like "MOMO:", "Assistant:", "AI:"
        cleaned = re.sub(r'^(?:MOMO|Assistant|AI):\s*', '', cleaned, flags=re.IGNORECASE)
        # Strip screenplay style prefixes like '"User", in a warm and helpful tone:' or 'User:'
        cleaned = re.sub(r'^["\']?User["\']?,\s*[^:]+:\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^User:\s*', '', cleaned, flags=re.IGNORECASE)

        # Strip placeholder echoes
        if cleaned.lower() in [
            "your direct, helpful, and accurate response to the user",
            "your conversational response in markdown text",
            "your conversational response",
            "<your response>",
            "<your helpful and accurate response>",
            "<your complete, articulate response here>"
        ]:
            cleaned = ""

        # Strip surrounding double or single quotes if wrapped
        if len(cleaned) >= 2 and ((cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'"))):
            cleaned = cleaned[1:-1].strip()

        # Sanitize cutoff disclaimers
        cleaned = cls.sanitize_cutoff_disclaimers(cleaned)
        return cleaned

    @classmethod
    def normalize_expression(cls, expr_raw: str) -> str:
        if not expr_raw:
            return "normal"
        e = str(expr_raw).strip().lower()
        if e in VALID_EXPRESSIONS:
            return e
        if any(w in e for w in ["happy", "smile", "joy", "grin", "glad", "laugh", "excited"]):
            return "happy"
        if any(w in e for w in ["think", "ponder", "wonder", "curious"]):
            return "thinking"
        if any(w in e for w in ["confuse", "puzzl", "what", "question", "doubt"]):
            return "confused"
        if any(w in e for w in ["sad", "sorry", "cry", "unhappy"]):
            return "sad"
        if any(w in e for w in ["sleep", "tired", "yawn"]):
            return "sleepy"
        if any(w in e for w in ["proud", "accomplish", "win"]):
            return "proud"
        if any(w in e for w in ["surpris", "shock", "wow"]):
            return "surprised"
        return "normal"

    @classmethod
    def normalize_animation(cls, anim_raw: str) -> str:
        if not anim_raw:
            return "none"
        a = str(anim_raw).strip().lower()
        if a in VALID_ANIMATIONS:
            return a
        if any(w in a for w in ["nod", "yes", "agree"]):
            return "nod"
        if any(w in a for w in ["wave", "hello", "hi"]):
            return "wave"
        if any(w in a for w in ["celebrate", "party", "cheer", "jump"]):
            return "celebrate"
        if any(w in a for w in ["left", "tilt"]):
            return "tilt_left"
        if any(w in a for w in ["right"]):
            return "tilt_right"
        if any(w in a for w in ["blink"]):
            return "blink"
        return "none"

    @classmethod
    def parse(cls, raw_text: str, thinking_text: Optional[str] = None, model: Optional[str] = None) -> MomoResponse:
        """
        Parses output string, extracting JSON payload or falling back to raw message.
        """
        cleaned = raw_text.strip() if raw_text else ""
        
        # 1. Try stripping markdown code fences: ```json ... ``` or ``` ... ```
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if fence_match:
            candidate = fence_match.group(1).strip()
        else:
            candidate = cleaned

        # 2. Try parsing candidate JSON
        parsed_dict = None
        try:
            parsed_dict = json.loads(candidate)
        except json.JSONDecodeError:
            # Try finding any embedded { ... } block
            bracket_match = re.search(r"\{[\s\S]*\}", candidate)
            if bracket_match:
                try:
                    parsed_dict = json.loads(bracket_match.group(0))
                except json.JSONDecodeError:
                    parsed_dict = None

        # 2b. If valid JSON parsing failed, recover fields via regex from partial/unclosed JSON
        if parsed_dict is None and ("{" in candidate or '"message"' in candidate):
            msg_match = re.search(r'"message"\s*:\s*"((?:[^"\\]|\\.)*)', candidate, re.DOTALL)
            if not msg_match:
                msg_match = re.search(r'"(?:content|response|text)"\s*:\s*"((?:[^"\\]|\\.)*)', candidate, re.DOTALL)

            expr_match = re.search(r'"expression"\s*:\s*"([^"]+)"', candidate, re.IGNORECASE)
            anim_match = re.search(r'"animation"\s*:\s*"([^"]+)"', candidate, re.IGNORECASE)

            if msg_match:
                extracted_msg = msg_match.group(1).replace('\\"', '"').replace('\\n', '\n').strip()
                extracted_msg = re.sub(r'["\}]+$', '', extracted_msg).strip()
                parsed_dict = {
                    "message": extracted_msg,
                    "expression": expr_match.group(1) if expr_match else "normal",
                    "animation": anim_match.group(1) if anim_match else "none"
                }

        # 3. If JSON parsed or recovered successfully, extract fields
        if isinstance(parsed_dict, dict):
            raw_msg = parsed_dict.get("message", "")
            if not raw_msg and "content" in parsed_dict:
                raw_msg = str(parsed_dict["content"])
            msg = cls.clean_text(str(raw_msg))
            expr = cls.normalize_expression(parsed_dict.get("expression", "normal"))
            anim = cls.normalize_animation(parsed_dict.get("animation", "none"))
            speak = bool(parsed_dict.get("speak", True))
            prio = parsed_dict.get("priority", "normal")

            if prio not in VALID_PRIORITIES:
                prio = "normal"

            if msg:
                return MomoResponse(
                    message=msg,
                    expression=expr,
                    animation=anim,
                    speak=speak,
                    priority=prio,
                    ascii=EXPRESSION_ASCII.get(expr, "◕ᴗ◕"),
                    thinking=thinking_text,
                    model=model
                )

        # 4. Fallback: LLM replied with plain text without JSON wrapper
        # Extract plain message, infer expression from keywords
        plain_msg = cls.clean_text(cleaned)
        if not plain_msg or plain_msg.strip() in ["{", "}", '""', "...", ""]:
            plain_msg = "I am at your service. Please let me know how I can assist you."

        inferred_expr = "normal"
        inferred_anim = "none"

        lower = plain_msg.lower()
        if any(w in lower for w in ["haha", "great", "yay", "awesome", "nice", "success"]):
            inferred_expr = "happy"
            inferred_anim = "nod"
        elif any(w in lower for w in ["hmm", "wait", "let me see", "thinking"]):
            inferred_expr = "thinking"
        elif any(w in lower for w in ["sorry", "unfortunately", "error", "failed"]):
            inferred_expr = "sad"
        elif any(w in lower for w in ["what?", "confused", "huh"]):
            inferred_expr = "confused"
            inferred_anim = "tilt_left"

        return MomoResponse(
            message=plain_msg,
            expression=inferred_expr,
            animation=inferred_anim,
            speak=True,
            priority="normal",
            ascii=EXPRESSION_ASCII.get(inferred_expr, "◕ᴗ◕"),
            thinking=thinking_text,
            model=model
        )
