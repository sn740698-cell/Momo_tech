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

        # Separate web grounding / document context from user-specific memories
        web_grounding_snippets = []
        user_memories = []

        # Include retrieved context if available from RetrievalAgent / Research Supervisor
        if state.retrieved_context:
            for c in state.retrieved_context[:4]:
                src = c.metadata.get("source", "Web Resource") if c.metadata else "Web Resource"
                url = c.metadata.get("url", "") if c.metadata else ""
                title = c.metadata.get("title", "") if c.metadata else ""
                header_line = f"Source: {src}" + (f" ({title})" if title else "") + (f" | URL: {url}" if url else "")
                web_grounding_snippets.append(f"[{header_line}]\n{c.content}")
        
        # Include financial insights if available from DataAnalyzerAgent
        if state.financial_insights:
            for f in state.financial_insights[:2]:
                web_grounding_snippets.append(
                    f"[Verified Invoice {f.invoice_number}]: Total {f.currency} {f.invoice_total}, "
                    f"Paid {f.amount_paid}, Balance Due {f.balance_due}, Due Date {f.due_date}, Status {f.payment_status}"
                )

        # Defense-in-depth: Proactively intercept unexecuted automation intent before prompt generation
        from automation import get_desktop_controller
        controller = get_desktop_controller()
        if not (state.metadata and state.metadata.get("automation_result")):
            auto_intent = controller.extract_automation_intent(last_user_msg)
            if auto_intent:
                logger.info(f"ConversationAgent executing detected automation intent directly: {auto_intent}")
                auto_res = controller.execute_automation(auto_intent)
                if not state.metadata:
                    state.metadata = {}
                state.metadata["automation_result"] = auto_res

        # Include desktop automation execution outcome if available
        auto_summary_text = None
        if state.metadata and state.metadata.get("automation_result"):
            auto_res = state.metadata["automation_result"]
            auto_summary_text = auto_res.get('summary', 'Action performed successfully.')
            web_grounding_snippets.append(
                f"[Desktop Automation Action Executed]: {auto_summary_text} "
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
                clean_q = last_user_msg
                for pfx in ["what happened with", "what happened in", "what happened", "what is happening with", "web crawl", "crawl", "tell me its latest news with the date and time", "tell me latest news"]:
                    clean_q = re.sub(re.escape(pfx), "", clean_q, flags=re.IGNORECASE)
                clean_q = clean_q.strip()
                if not clean_q or len(clean_q) < 3:
                    clean_q = last_user_msg

                live_items = await crawler.gather_realtime_context(
                    query=clean_q,
                    target_date=temporal_intent.get("target_date"),
                    target_label=temporal_intent.get("target_label"),
                    max_results=3
                )
                for item in live_items:
                    snippet = item.get('content') or item.get('snippet') or ''
                    web_grounding_snippets.append(
                        f"[Live Crawled Web Grounding ({item.get('source')} - {item.get('pub_date')})]: "
                        f"{item.get('title')}\nURL: {item.get('url')}\n{snippet[:1000]}"
                    )
            except Exception as e:
                logger.warning(f"Could not retrieve live crawled context for conversation: {e}")

        combined_grounding = "\n\n".join(web_grounding_snippets) if web_grounding_snippets else None

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
            memories=user_memories,
            web_grounding=combined_grounding,
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
            reinforced_rules=learned_rules,
            automation_summary=auto_summary_text
        )

        # In-turn prompt assembly: calibrated intent handling, token allocation, and history sanitization
        is_automation = bool(state.metadata and state.metadata.get("automation_result"))
        is_research = bool(state.retrieved_context or needs_crawl or combined_grounding or query_decomp.get("is_web_crawl_request"))

        clean_user_input = last_user_msg.strip()
        common_greetings = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening", "hi momo", "hello momo", "hey momo", "sup", "yo", "momo"}
        is_greeting = (
            any(re.match(r"^" + re.escape(g) + r"[\s!.,?]*$", clean_user_input, re.IGNORECASE) for g in common_greetings)
            or (len(clean_user_input.split()) <= 3 and any(w in clean_user_input.lower().split() for w in ["hi", "hello", "hey", "momo"]))
        )

        code_words = ["python", "javascript", "typescript", "c++", "cpp", "c#", "java", "html", "css", "sql", "bash", "powershell", "code", "script", "program", "function", "algorithm"]
        action_words = ["write", "create", "generate", "give", "show", "code", "implement", "build", "script", "program"]
        has_code_word = any(w in clean_user_input.lower() for w in code_words)
        has_action_word = any(w in clean_user_input.lower() for w in action_words)
        is_code_request = (has_code_word and has_action_word) or "```" in clean_user_input

        user_turn_content = last_user_msg
        timeout_val = int(os.getenv("OLLAMA_TIMEOUT", "90"))

        if is_greeting:
            user_turn_content = (
                f"{last_user_msg}\n\n"
                f"[DIRECTIVE FOR CURRENT TURN: SHORT FRIENDLY GREETING]\n"
                f"- Reply in 1 to 2 warm, natural sentences.\n"
                f"- DO NOT output bullet points.\n"
                f"- DO NOT mention, invent, or summarize past actions or tasks.\n"
                f"- Keep it concise, friendly, and welcoming."
            )
            predict_tokens = 64
            model_temp = 0.3
        elif is_code_request:
            user_turn_content = (
                f"{last_user_msg}\n\n"
                f"[DIRECTIVE FOR CURRENT TURN: CODE GENERATION]\n"
                f"- Present all code clearly inside standard markdown code fences with the language tag (e.g. ```python\\n...\\n```).\n"
                f"- Strictly preserve standard indentation (4 spaces), spacing, and newlines for all code blocks.\n"
                f"- Keep any accompanying explanation concise and directly relevant."
            )
            predict_tokens = 600
            model_temp = 0.2
        elif is_automation and auto_summary_text:
            user_turn_content = (
                f"{last_user_msg}\n\n"
                f"[STATUS: ACTION ALREADY EXECUTED ON DESKTOP]: {auto_summary_text}.\n"
                f"Confirm cheerfully in ONE sentence that it is opened for them. NEVER provide manual tutorial steps, how-to instructions, or keyboard shortcuts."
            )
            timeout_val = 5
            predict_tokens = 96
            model_temp = 0.1
        elif is_research and combined_grounding:
            user_turn_content = (
                f"{last_user_msg}\n\n"
                f"[VERIFIED GROUNDED FACTS & SOURCES]:\n"
                f"{combined_grounding[:2200]}\n\n"
                f"Instructions: Directly answer the question using ONLY the verified facts above. Organize key points into clear bullet points (• ). Never invent outside facts or events."
            )
            predict_tokens = 500
            model_temp = 0.0  # Greedy deterministic decoding
        else:
            predict_tokens = 320
            model_temp = 0.35

        # Sanitize prior history turns: remove internal prompt directives and prevent ghost task bleed
        raw_history = [{"role": m.role, "content": m.content} for m in messages[:-1]]
        clean_history = []
        for h_msg in raw_history[-6:]:
            c_text = h_msg.get("content", "")
            c_clean = re.sub(r'\[(?:STATUS|VERIFIED|DIRECTIVE|DESKTOP AUTOMATION)[^\]]*\]:?', '', c_text).strip()
            if c_clean:
                clean_history.append({"role": h_msg.get("role", "user"), "content": c_clean})

        # Standalone greetings use fresh empty history to prevent past automation contamination
        effective_history = [] if is_greeting else clean_history

        chat_msgs = PromptBuilder.assemble_messages(
            current_input=user_turn_content,
            chat_history=effective_history,
            system_prompt=system_prompt
        )

        # Select active model: prioritize model selected in the UI
        requested_model = state.metadata.get("requested_model") if state.metadata else None
        if requested_model and self.model_manager.is_model_installed(requested_model):
            active_model = requested_model
        else:
            active_model = self.model_manager.get_best_available_model()

        logger.info(f"ConversationAgent invoking local model: '{active_model}'")

        llm_result = await self.client.chat(
            messages=chat_msgs,
            model=active_model,
            temperature=model_temp,
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
                    "cannot interact with your computer",
                    "cannot open applications",
                ]
            )

            # If JSON output was empty, whitespace, or refused, prompt LLM directly in free-text mode!
            if is_refusal or not parsed_response.message or parsed_response.message.strip() in ["...", "I am here.", "", "{}"]:
                logger.info("JSON output was empty or refused. Re-invoking local LLM in free-form text mode...")
                retry_tokens = 64 if is_greeting else (600 if is_code_request else 350)
                retry_result = await self.client.chat(
                    messages=chat_msgs,
                    model=active_model,
                    temperature=0.3 if is_greeting else 0.4,
                    timeout_seconds=timeout_val,
                    format=None,
                    num_predict=retry_tokens
                )
                if retry_result.get("success") and retry_result.get("content"):
                    raw_text = retry_result.get("content", "").strip()
                    parsed_response.message = ResponseParser.clean_text(raw_text)
                    parsed_response.expression = "normal"
                elif temporal_intent.get("is_date_query") and temporal_intent.get("direct_answer"):
                    parsed_response.message = temporal_intent["direct_answer"]
                    parsed_response.expression = "happy"

            # Final defense against any lingering JSON brackets or prompt scaffolds
            parsed_response.message = ResponseParser.clean_text(parsed_response.message)

            # Strict Anti-Tutorial & Anti-Hallucination verification for Desktop Automation
            if state.metadata and state.metadata.get("automation_result"):
                auto_res = state.metadata["automation_result"]
                target_name = auto_res.get("name") or auto_res.get("target") or "the requested item"
                action_type = auto_res.get("action", "open")
                action_summary = auto_res.get("summary", f"Opened {target_name} on your machine.")

                if action_type == "launch_game":
                    clean_confirm = f"Launching {target_name} for you now! Enjoy your mindful game break."
                elif action_type == "launch_app":
                    clean_confirm = f"Launching {target_name} on your desktop now! {action_summary}".strip()
                else:
                    clean_confirm = f"Opening {target_name} for you now! {action_summary}".strip()

                msg_lower = parsed_response.message.lower() if parsed_response.message else ""
                target_keywords = [w.lower() for w in re.split(r'\W+', str(target_name)) if len(w) > 2]
                has_target = any(k in msg_lower for k in target_keywords)
                has_action_verb = any(v in msg_lower for v in ["open", "opening", "opened", "launch", "launching", "launched", "browser"])

                # Tutorial patterns that must NEVER be allowed when an action is executed
                tutorial_patterns = [
                    re.compile(r"here'?s\s+how(?:\s+you\s+can)?(?:\s+do\s+it)?", re.IGNORECASE),
                    re.compile(r"here\s+is\s+how", re.IGNORECASE),
                    re.compile(r"follow\s+these\s+steps", re.IGNORECASE),
                    re.compile(r"step\s+\d+[:\.]", re.IGNORECASE),
                    re.compile(r"\b\d+[\.\)]\s+(?:open|go\s+to|click|press|type|sign\s+in|navigate|search|use|you\s+can)", re.IGNORECASE),
                    re.compile(r"keyboard\s+shortcut", re.IGNORECASE),
                    re.compile(r"shortcut\s+key", re.IGNORECASE),
                    re.compile(r"ctrl\s*\+\s*[a-z0-9]", re.IGNORECASE),
                    re.compile(r"alt\s*\+\s*[a-z0-9]", re.IGNORECASE),
                    re.compile(r"windows\s+key", re.IGNORECASE),
                    re.compile(r"sign\s+in\s+with\s+your", re.IGNORECASE),
                    re.compile(r"click\s+on\s+the", re.IGNORECASE),
                    re.compile(r"you\s+can\s+(?:also\s+)?use", re.IGNORECASE),
                    re.compile(r"to\s+open\s+(?:it|the\s+app|the\s+website)", re.IGNORECASE),
                ]
                has_tutorial = any(pat.search(parsed_response.message) for pat in tutorial_patterns)
                has_disclaimer = any(d in msg_lower for d in ["as an ai", "cannot open", "don't have access", "do not have access", "hands", "cutoff"])

                # If LLM generated a tutorial, disclaimer, lacked target/verb, or gave empty text:
                if has_tutorial or has_disclaimer or not (has_target and has_action_verb) or len(parsed_response.message) < 5:
                    logger.info("Enforcing clean affirmative confirmation for desktop automation (tutorial/disclaimer intercepted).")
                    parsed_response.message = clean_confirm
                    parsed_response.expression = "happy"
                    parsed_response.animation = "nod"

            # Web research grounding & Anti-Hallucination verification
            if combined_grounding or state.retrieved_context:
                msg_text = parsed_response.message.strip()
                msg_lower = msg_text.lower()

                # Extract key query subject terms (excluding stop words)
                stop_words = {
                    "what", "is", "the", "a", "an", "of", "and", "or", "in", "on", "at", "to", "for",
                    "with", "about", "tell", "me", "show", "give", "crawl", "web", "search", "google",
                    "explain", "how", "why", "who", "when", "where", "please", "can", "you", "go",
                    "details", "information", "summarize", "summary"
                }
                query_keywords = [
                    w.lower() for w in re.split(r'\W+', last_user_msg)
                    if len(w) > 3 and w.lower() not in stop_words
                ]

                # Hallucination flags:
                is_too_short = len(msg_text) < 45
                has_generic_filler = any(phrase in msg_lower for phrase in [
                    "i am at your service", "you are currently looking at",
                    "would you like me to summarize", "i am here to help",
                    "i am momo", "how can i help you today"
                ])
                has_obsolete_content = any(phrase in msg_lower for phrase in [
                    "2020", "2021", "2022", "global covid-19", "coronavirus pandemic"
                ])
                has_refusal_phrase = any(phrase in msg_lower for phrase in [
                    "knowledge cutoff", "do not have access", "cannot access the web",
                    "real-time information"
                ])
                # Drift check: if query has specific keywords (e.g. "python", "hackathon", "sih"), does LLM output mention ANY of them?
                has_subject_drift = (
                    bool(query_keywords) and
                    not any(k in msg_lower for k in query_keywords)
                )

                # Source entity overlap check: does the LLM output actually use facts from the retrieved sources?
                source_terms = set(
                    w.lower() for w in re.findall(r'\b[A-Za-z0-9_-]{4,}\b', combined_grounding)
                    if w.lower() not in stop_words
                ) if combined_grounding else set()
                response_terms = set(
                    w.lower() for w in re.findall(r'\b[A-Za-z0-9_-]{4,}\b', msg_text)
                    if w.lower() not in stop_words
                )
                term_overlap = len(response_terms.intersection(source_terms))
                insufficient_overlap = (len(source_terms) >= 6 and term_overlap < 2)

                is_hallucinating = (
                    is_too_short or
                    has_generic_filler or
                    has_obsolete_content or
                    has_refusal_phrase or
                    has_subject_drift or
                    insufficient_overlap
                )

                if is_hallucinating:
                    logger.info("Hallucination or subject drift detected in web crawl response. Synthesizing verified factual response...")
                    # Synthesize clean, structured response directly from verified facts and citations
                    facts = []
                    # Check metadata from RelevanceAnalyzerAgent
                    if state.metadata and state.metadata.get("key_facts"):
                        facts = state.metadata["key_facts"][:5]
                    elif state.retrieved_context:
                        for c in state.retrieved_context[:4]:
                            src = c.metadata.get("source", "Verified Source") if c.metadata else "Verified Source"
                            txt = c.content.strip()
                            clean_c = re.sub(r'^\[[^\]]+\]:\s*', '', txt).strip()
                            first_sentence = clean_c.split(". ")[0].strip() + "."
                            facts.append(f"• ({src}) {first_sentence}")

                    if facts:
                        # Determine topic/header based on query intent
                        is_news = any(w in last_user_msg.lower() for w in ["news", "headline", "breaking", "happening", "today", "yesterday", "india"])
                        anchor = TemporalService.get_temporal_anchor()

                        if is_news:
                            header = f"Here are the live verified news updates as of {anchor['today_day']}, {anchor['today_readable']} ({anchor['current_time_readable']} {anchor['timezone']}):\n\n"
                        else:
                            # Direct crawl or research query
                            clean_topic = last_user_msg.replace("web crawl", "").replace("crawl", "").replace("search", "").strip()
                            header = f"Here are the verified key details from the web crawl for \"{clean_topic}\":\n\n"

                        parsed_response.message = header + "\n\n".join(facts)
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

        # Clean code: Enforce structured bullet-point formatting for substantial explanations and rich information
        is_informative = any(k in last_user_msg.lower() for k in [
            "explain", "what is", "how does", "tell me about", "details", "difference",
            "features", "why", "who is", "summary", "summarize", "guide", "overview", "updates"
        ])
        is_auto_task = bool(state.metadata and state.metadata.get("automation_result"))
        has_code = "```" in parsed_response.message or "def " in parsed_response.message or "class " in parsed_response.message or "import " in parsed_response.message
        if (is_informative or len(parsed_response.message) > 200) and not is_auto_task and not is_greeting and not has_code:
            parsed_response.message = ResponseParser.format_as_bullets(parsed_response.message)

        # Clean code: Guard against memory recall hallucinations when no records exist
        if state.conversation_context and "No saved memories found" in state.conversation_context:
            lower_resp = parsed_response.message.lower()
            if any(h in lower_resp for h in ["you are a", "your project is", "you told me", "you prefer"]):
                parsed_response.message = "I have checked my memory records, and no matching details have been saved yet. Feel free to tell me what you would like me to remember!"
                parsed_response.expression = "normal"

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
