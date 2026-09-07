from datetime import datetime
from typing import List, Dict, Any, Optional
from brain.personality import BASE_SYSTEM_PROMPT
from ai_workflow.services.temporal_service import TemporalService


class PromptBuilder:
    """
    Constructs contextual, persona-aligned prompts merging:
    1. MOMO Persona & JSON Schema contract
    2. User Identity & Long-Term Memories
    3. Live Session & Context Telemetry (Active app, idle time, session length)
    4. Deterministic Temporal Anchor (Date, Day, Yesterday, Observances, Timezone)
    5. Multi-turn Chat History
    """

    @classmethod
    def build_system_prompt(
        cls,
        user_name: str = "User",
        memories: Optional[List[str]] = None,
        active_app: str = "",
        session_minutes: int = 0,
        idle_seconds: int = 0,
        custom_instructions: Optional[str] = None
    ) -> str:
        prompt_parts = [BASE_SYSTEM_PROMPT]

        # Deterministic Temporal & Environmental Grounding
        anchor = TemporalService.get_temporal_anchor()
        context_block = [
            f"- Current Date & Day: {anchor['today_day']}, {anchor['today_readable']} ({anchor['today_date']})",
            f"- Current Time: {anchor['current_time_readable']} ({anchor['timezone']})",
            f"- Yesterday Was: {anchor['yesterday_day']}, {anchor['yesterday_readable']} ({anchor['yesterday_date']})",
        ]
        if anchor.get("special_today"):
            context_block.append(f"- Today's Observance: {anchor['special_today']}")
        if user_name and user_name.lower() not in ["user", "unknown", ""]:
            context_block.append(f"- User Name: {user_name}")
        if active_app:
            context_block.append(f"- Active Window/App: {active_app}")
        if session_minutes > 0:
            context_block.append(f"- Session Duration: {session_minutes} minutes")
        if idle_seconds > 0:
            context_block.append(f"- Idle Time: {idle_seconds} seconds")

        prompt_parts.append("\n[TELEMETRY & ENVIRONMENT]\n" + "\n".join(context_block))

        # Long-term memory block
        if memories and len(memories) > 0:
            memory_lines = [f"- {m}" for m in memories]
            prompt_parts.append("\nSTORED FACTS ABOUT USER:\n" + "\n".join(memory_lines))

        # Additional instructions
        if custom_instructions:
            prompt_parts.append(f"\nADDITIONAL INSTRUCTIONS:\n{custom_instructions}")

        return "\n\n".join(prompt_parts)

    @classmethod
    def assemble_messages(
        cls,
        current_input: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if chat_history:
            for msg in chat_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if content:
                    messages.append({"role": role, "content": content})

        if current_input:
            messages.append({"role": "user", "content": current_input})

        return messages
