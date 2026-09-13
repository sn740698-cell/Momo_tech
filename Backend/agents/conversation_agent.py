"""
Conversation Agent for MOMO.
Handles conversational dialogue, humor, emotional persona, and Ollama local LLM execution.
"""
import os
import re
import time
import logging
from typing import Dict, Any, Optional

from graph.state import MomoState, Message, MomoResponse, HardwareCommand, RoutingDecision
from ai.ollama_client import OllamaClient
from ai.model_manager import ModelManager
from ai.prompt_builder import PromptBuilder
from ai.response_parser import ResponseParser
from brain.personality import EXPRESSION_ASCII
from security.permissions import PermissionManager
from ai_workflow.services.temporal_service import TemporalService
from ai_workflow.services.web_crawler_service import LiveWebCrawlerService
from ai.query_chunker import QueryChunker

logger = logging.getLogger(__name__)


class ConversationAgent:
    """
    Executes conversational turn within the LangGraph workflow.
    """

    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self.client = ollama_client or OllamaClient()
        self.model_manager = ModelManager(self.client)

    async def run(self, state: MomoState) -> Dict[str, Any]:
        """
        Executes conversation node. Takes MomoState, invokes Ollama,
        and returns updated state contribution dictionary.
        """
        messages = state.messages
        last_user_msg = ""
        for m in reversed(messages):
            if m.role == "user":
                last_user_msg = m.content
                break

        if not last_user_msg:
            last_user_msg = state.voice_input or "Hello"

        # Build prompt incorporating retrieved memory & context
        active_app = state.user_context.active_app if state.user_context else "Desktop"
        session_mins = state.user_context.session_duration_minutes if state.user_context else 0
        idle_secs = state.user_context.idle_seconds if state.user_context else 0

        # Include retrieved context if available from RetrievalAgent
        context_snippets = []
        if state.retrieved_context:
            for c in state.retrieved_context[:3]:
                context_snippets.append(f"[Document Context]: {c.content}")
        
        # Include financial insights if available from DataAnalyzerAgent
        if state.financial_insights:
            for f in state.financial_insights[:2]:
                context_snippets.append(
                    f"[Verified Invoice {f.invoice_number}]: Total {f.currency} {f.invoice_total}, "
                    f"Paid {f.amount_paid}, Balance Due {f.balance_due}, Due Date {f.due_date}, Status {f.payment_status}"
                )

        # Include desktop automation execution outcome if available from AutomationAgent
        if state.metadata and state.metadata.get("automation_result"):
            auto_res = state.metadata["automation_result"]
            context_snippets.append(
                f"[Desktop Automation Action Executed]: {auto_res.get('summary', 'Action performed successfully.')} "
                f"(Target: {auto_res.get('target')}, Action: {auto_res.get('action')}, Status: {'Success' if auto_res.get('success') else 'Failed'})"
            )

        # Deconstruct and semantically chunk the user query for thorough comprehension
        query_decomp = QueryChunker.decompose(last_user_msg)

        # Check for web crawl, direct URL, or temporal search intent (if not already crawled by WebCrawlAgent)
        temporal_intent = TemporalService.analyze_temporal_intent(last_user_msg)
        needs_crawl = (
            not state.retrieved_context and (
                query_decomp.get("is_web_crawl_request", False)
                or bool(query_decomp.get("urls"))
                or (temporal_intent.get("needs_web_search") and not temporal_intent.get("is_date_query"))
            )
        )

        if needs_crawl:
            try:
                crawler = LiveWebCrawlerService(timeout_seconds=15.0)
                clean_q = last_user_msg.replace("what happened with", "").replace("what happened", "").strip()
                live_items = await crawler.gather_realtime_context(
                    query=clean_q,
                    target_date=temporal_intent.get("target_date"),
                    target_label=temporal_intent.get("target_label"),
                    max_results=3
                )
                for item in live_items:
                    snippet = item.get('content') or item.get('snippet') or ''
                    context_snippets.append(
                        f"[Live Crawled Web Grounding ({item.get('source')} - {item.get('pub_date')})]: "
                        f"{item.get('title')}\nURL: {item.get('url')}\n{snippet[:1000]}"
                    )
            except Exception as e:
                logger.warning(f"Could not retrieve live crawled context for conversation: {e}")

        combined_context = "\n".join(context_snippets) if context_snippets else None

        # Incorporate LangGraph agent intent understanding & directives
        agent_directive = None
        if state.conversation_context:
            agent_directive = f"[AGENT QUERY UNDERSTANDING & DIRECTIVE]:\n{state.conversation_context}"

        # Vision & Emotional Perception Telemetry
        vision = state.vision_state
        user_emotion = vision.emotion if vision else None
        fatigue_detected = vision.fatigue_detected if vision else False
        looking_at_momo = vision.looking_at_camera if vision else False
        work_mins = vision.work_duration_minutes if vision else float(session_mins)
        proactive_trigger = vision.proactive_trigger if vision else None

        # Fetch active reinforced rules learned from user input
        learned_rules = []
        try:
            from memory.memory_manager import MemoryManager
            mem_mgr = MemoryManager()
            learned_rules = await mem_mgr.get_active_reinforced_rules(limit=5)
        except Exception:
            pass

        system_prompt = PromptBuilder.build_system_prompt(
            user_name="User",
            memories=[combined_context] if combined_context else [],
            active_app=active_app,
            session_minutes=session_mins,
            idle_seconds=idle_secs,
            custom_instructions=agent_directive,
            user_emotion=user_emotion,
            fatigue_detected=fatigue_detected,
            looking_at_momo=looking_at_momo,
            work_duration_minutes=work_mins,
            proactive_trigger=proactive_trigger,
            query_decomposition=query_decomp,
            reinforced_rules=learned_rules
        )

        history = [{"role": m.role, "content": m.content} for m in messages[:-1]]
        chat_msgs = PromptBuilder.assemble_messages(
            current_input=last_user_msg,
            chat_history=history[-6:],
            system_prompt=system_prompt
        )

        # Select active model: prioritize model selected in the UI
        requested_model = state.metadata.get("requested_model") if state.metadata else None
        if requested_model and self.model_manager.is_model_installed(requested_model):
            active_model = requested_model
        else:
            active_model = self.model_manager.get_best_available_model()

        logger.info(f"ConversationAgent invoking local model: '{active_model}'")

        # Fast generation: calibrated predict tokens (48 for automation, 480 for research, 280 for conversation)
        is_automation = bool(state.metadata and state.metadata.get("automation_result"))
        if is_automation:
            timeout_val = 5  # Fast sub-second path for automation commands
            predict_tokens = 48
        else:
            timeout_val = int(os.getenv("OLLAMA_TIMEOUT", "90"))
            predict_tokens = 480 if state.retrieved_context else 280

        llm_result = await self.client.chat(
            messages=chat_msgs,
            model=active_model,
            temperature=0.35,
            timeout_seconds=timeout_val,
            format=None,
            num_predict=predict_tokens
        )

        if llm_result.get("success"):
            raw_content = llm_result.get("content", "")
            thinking = llm_result.get("thinking", "")
            parsed_response = ResponseParser.parse(raw_content, thinking, active_model)

            # Strict guard against knowledge cutoff disclaimers and JSON leaks
            msg_lower = parsed_response.message.lower()
            is_refusal = any(
                phrase in msg_lower for phrase in [
                    "knowledge cutoff",
                    "as of my current",
                    "as of my knowledge",
                    "real-time",
                    "as an ai",
                    "cannot provide real-time",
                    "don't have access",
                    "do not have access",
                ]
            )

            # If JSON output was empty, whitespace, or refused, prompt LLM directly in free-text mode!
            if is_refusal or not parsed_response.message or parsed_response.message.strip() in ["...", "I am here.", "", "{}"]:
                logger.info("JSON output was empty or refused. Re-invoking local LLM in free-form text mode...")
                retry_result = await self.client.chat(
                    messages=chat_msgs,
                    model=active_model,
                    temperature=0.4,
                    timeout_seconds=timeout_val,
                    format=None,
                    num_predict=640
                )
                if retry_result.get("success") and retry_result.get("content"):
                    raw_text = retry_result.get("content", "").strip()
                    parsed_response.message = ResponseParser.clean_text(raw_text)
                    parsed_response.expression = "normal"
                elif temporal_intent.get("is_date_query") and temporal_intent.get("direct_answer"):
                    parsed_response.message = temporal_intent["direct_answer"]
                    parsed_response.expression = "happy"

            # Final defense against any lingering JSON brackets
            parsed_response.message = ResponseParser.clean_text(parsed_response.message)

            # Enforce explicit confirmation if desktop automation was executed
            if state.metadata and state.metadata.get("automation_result"):
                auto_res = state.metadata["automation_result"]
                target_name = auto_res.get("name") or auto_res.get("target") or "the requested item"
                action_type = auto_res.get("action", "open")
                action_summary = auto_res.get("summary", f"Opened {target_name} on your machine.")

                msg_lower = parsed_response.message.lower() if parsed_response.message else ""
                target_keywords = [w.lower() for w in re.split(r'\W+', str(target_name)) if len(w) > 2]
                has_target = any(k in msg_lower for k in target_keywords)
                has_action_verb = any(v in msg_lower for v in ["open", "opening", "opened", "launch", "launching", "launched", "browser"])

                # If LLM failed to state that it is opening the target, or gave a generic greeting/empty text:
                if not (has_target and has_action_verb) or not parsed_response.message or len(parsed_response.message) < 5:
                    if action_type == "launch_game":
                        prefix = f"Launching {target_name} for you now!"
                    elif action_type == "launch_app":
                        prefix = f"Launching {target_name} on your desktop now!"
                    else:
                        prefix = f"Opening {target_name} for you now!"

                    parsed_response.message = f"{prefix} {action_summary}".strip()
                    parsed_response.expression = "happy"
                    parsed_response.animation = "nod"

            # Web research grounding reinforcement: ensure substantive answers when retrieved context exists
            has_generic_or_hallucinated_news = (
                state.retrieved_context and (
                    len(parsed_response.message.strip()) < 45
                    or "I am at your service" in parsed_response.message
                    or "You are currently looking at the latest news" in parsed_response.message
                    or "Would you like me to summarize" in parsed_response.message
                    or "2022" in parsed_response.message
                    or "Global COVID-19 Cases" in parsed_response.message
                )
            )
            if has_generic_or_hallucinated_news:
                top_facts = []
                for c in state.retrieved_context[:4]:
                    txt = c.content.strip()
                    title = c.metadata.get("title", "")
                    src = c.metadata.get("source", "Verified News")
                    if title and title not in [t.split("] ")[-1].split("\n")[0] for t in top_facts]:
                        clean_c = re.sub(r'^\[[^\]]+\]:\s*', '', txt).strip()
                        summary_txt = clean_c[:220] if clean_c and clean_c != title else ""
                        item_str = f"• [{src}] {title}" + (f"\n  {summary_txt}" if summary_txt else "")
                        top_facts.append(item_str)
                if top_facts:
                    anchor = TemporalService.get_temporal_anchor()
                    header = f"Here are the latest live verified news headlines as of {anchor['today_day']}, {anchor['today_readable']} ({anchor['current_time_readable']} {anchor['timezone']}):\n\n"
                    parsed_response.message = header + "\n\n".join(top_facts[:4])
                    parsed_response.expression = "thinking"
                    parsed_response.animation = "nod"

            # Temporal grounding: if user asks for date and time, ensure it is included
            if any(w in last_user_msg.lower() for w in ["date and time", "current date", "what is the date", "what is the time"]):
                anchor = TemporalService.get_temporal_anchor()
                anchor_mention = f"Today is {anchor['today_day']}, {anchor['today_readable']} ({anchor['current_time_readable']} {anchor['timezone']})."
                if not parsed_response.message.startswith("Today is"):
                    parsed_response.message = f"{anchor_mention}\n\n{parsed_response.message}"

            # Response verification against decomposed query chunks
            coverage = QueryChunker.verify_response_coverage(query_decomp, parsed_response.message)
            if not coverage.get("complete"):
                missing = coverage.get("missing_chunks", [])
                for m in missing:
                    if m.get("intent_type") == "emotional_support" and not any(w in parsed_response.message.lower() for w in ["understand", "care", "proud", "breathe", "rest"]):
                        parsed_response.message = (
                            "I hear you, and I completely understand how demanding and stressful it can be when you're working so hard. "
                            "Take a gentle breath — you're making real progress.\n\n" + parsed_response.message
                        )
        else:
            # Graceful degraded response when Ollama is unreachable or timed out
            err = str(llm_result.get("error", "Local LLM service unavailable."))
            logger.warning(f"Ollama chat error: {err}")

            # 1. First Priority: Automation action execution confirmation
            if state.metadata and state.metadata.get("automation_result"):
                auto_res = state.metadata["automation_result"]
                target_name = auto_res.get("name") or auto_res.get("target") or "the requested item"
                action_type = auto_res.get("action", "open")
                action_summary = auto_res.get("summary", f"Opened {target_name} on your machine.")
                if action_type == "launch_game":
                    msg = f"Launching {target_name} for you now! Enjoy your mindful game break."
                elif action_type == "launch_app":
                    msg = f"Launching {target_name} on your desktop now!"
                else:
                    msg = f"Opening {target_name} for you now! {action_summary}"
                parsed_response = MomoResponse(
                    message=msg,
                    expression="happy",
                    animation="nod",
                    speak=True,
                    priority="normal",
                    model=active_model
                )
            # 2. Second Priority: Live retrieved web / news context
            elif state.retrieved_context:
                top_facts = []
                for c in state.retrieved_context[:4]:
                    src = c.metadata.get("source", "Verified Source")
                    title = c.metadata.get("title", "")
                    clean_c = re.sub(r'^\[[^\]]+\]:\s*', '', c.content.strip()).strip()
                    item_str = f"• [{src}] {title}" + (f"\n  {clean_c[:200]}" if clean_c and clean_c != title else "")
                    top_facts.append(item_str)
                anchor = TemporalService.get_temporal_anchor()
                msg = f"Here is the latest live information as of {anchor['today_day']}, {anchor['today_readable']} ({anchor['current_time_readable']} {anchor['timezone']}):\n\n" + "\n\n".join(top_facts[:4])
                parsed_response = MomoResponse(
                    message=msg,
                    expression="thinking",
                    animation="nod",
                    speak=True,
                    priority="normal",
                    model=active_model
                )
            # 3. Third Priority: Deterministic date/time query
            elif temporal_intent.get("is_date_query") and temporal_intent.get("direct_answer"):
                parsed_response = MomoResponse(
                    message=temporal_intent["direct_answer"],
                    expression="happy",
                    animation="nod",
                    speak=True,
                    priority="normal",
                    model=active_model
                )
            else:
                if "timed out" in err.lower():
                    err_msg = f"My local AI model '{active_model}' took a moment to load into memory. I'm warm and ready now — please try asking your question again!"
                elif "not found" in err.lower():
                    err_msg = f"Model '{active_model}' was not found in your local Ollama library. Please select an installed model from the dropdown above."
                else:
                    err_msg = "My brain is buffering right now. Ensure Ollama is running on port 11434!"

                parsed_response = MomoResponse(
                    message=err_msg,
                    expression="confused",
                    animation="tilt_left",
                    speak=True,
                    priority="normal",
                    ascii="(o_o)?",
                    model=active_model
                )

        # Build assistant message
        asst_msg = Message(
            role="assistant",
            content=parsed_response.message,
            expression=parsed_response.expression,
            animation=parsed_response.animation,
            thinking=parsed_response.thinking
        )

        # Build validated hardware command for ESP32
        _, hw_cmd, _ = PermissionManager.validate_hardware_command({
            "expression": parsed_response.expression,
            "animation": parsed_response.animation,
            "speak": parsed_response.speak
        })

        hardware_cmd = HardwareCommand(**hw_cmd)

        return {
            "messages": [asst_msg],
            "response": parsed_response,
            "momo_expression": parsed_response.expression,
            "momo_animation": parsed_response.animation,
            "hardware_command": hardware_cmd,
            "current_agent": "conversation_agent"
        }
