"""
Query Decomposition, Semantic Chunking & LLM Comprehension Verification Engine.
Deconstructs complex, multi-part, and compound user inputs into discrete sub-goals
so the LLM companion thoroughly understands, covers, and accurately answers every aspect.
"""
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class QueryChunk:
    chunk_id: int
    text: str
    intent_type: str  # 'emotional_support', 'factual_inquiry', 'action_request', 'personal_banter', 'calculation'
    topics: List[str] = field(default_factory=list)
    must_address: bool = True
    guidance: str = ""


class QueryChunker:
    """
    Decomposes user queries into discrete semantic chunks and generates
    strict comprehension checklists for LLM grounding and verification.
    """

    CONJUNCTION_SPLITTERS = [
        r"\b(?:and\s+also|and\s+then|plus|furthermore|as\s+well\s+as)\b",
        r"\b(?:and|also|additionally|but)\b(?=\s+(?:can\s+you|could\s+you|please|what\s+is|tell\s+me|give\s+me|how|why|i\s+feel|i\s+am))",
        r",\s*(?=(?:can\s+you|could\s+you|please|what\s+is|tell\s+me|give\s+me|how|why|explain|and))",
        r"(?<=[.?!;])\s+",
        r"\n+",
    ]

    EMOTIONAL_KEYWORDS = {
        "stressed": ["stress", "stressed", "overwhelmed", "pressure", "burnout", "anxious", "frustrated", "bug for hours", "stuck for"],
        "tired": ["tired", "exhausted", "sleepy", "drowsy", "no rest", "overnight", "working so long", "fatigue"],
        "sad": ["sad", "depressed", "lonely", "alone", "down", "unhappy", "hopeless"],
        "happy": ["happy", "excited", "thrilled", "great day", "awesome", "celebrate", "built something"],
        "bored": ["bored", "boring", "need a break", "distract me", "play something"],
    }

    TECH_PATTERNS = [
        r"\b(?:python|javascript|typescript|c\+\+|rust|java|html|css|sql)\b",
        r"\b(?:event\s+loop|asyncio|coroutine|closure|decorator|generator|thread|process)\b",
        r"\b(?:api|endpoint|websocket|rest|asgi|django|react|vite|onnx|opencv)\b",
        r"\b(?:docker|kubernetes|git|github|linux|windows|esp32|servo|oled)\b",
    ]

    @classmethod
    def decompose(cls, user_text: str) -> Dict[str, Any]:
        """
        Deconstructs a user query into semantic chunks with entities, sentiment,
        and an explicit LLM comprehension plan.
        """
        raw = user_text.strip()
        if not raw:
            return {
                "original_query": "",
                "chunks": [],
                "primary_intent": "empty",
                "detected_emotions": [],
                "entities": [],
                "comprehension_directive": "",
            }

        # 1. Detect emotional sentiment in user text
        lower = raw.lower()
        detected_emotions = []
        for emo, keywords in cls.EMOTIONAL_KEYWORDS.items():
            if any(k in lower for k in keywords):
                detected_emotions.append(emo)

        # 2. Extract technical entities / topics
        entities = []
        for pat in cls.TECH_PATTERNS:
            matches = re.findall(pat, lower, re.IGNORECASE)
            for m in matches:
                if m not in entities:
                    entities.append(m)

        # 3. Semantic sentence & conjunction splitting
        raw_segments = [raw]
        # Split across clauses
        for splitter in cls.CONJUNCTION_SPLITTERS:
            new_segments = []
            for seg in raw_segments:
                parts = re.split(splitter, seg, flags=re.IGNORECASE)
                for p in parts:
                    clean_p = p.strip()
                    if clean_p:
                        new_segments.append(clean_p)
            raw_segments = new_segments

        # Merge ultra-short fragments (< 3 words) with adjacent segment
        merged_segments = []
        for seg in raw_segments:
            words = seg.split()
            if merged_segments and len(words) <= 2 and not any(q in seg for q in ["?", "why", "how", "what"]):
                merged_segments[-1] = f"{merged_segments[-1]}, {seg}"
            else:
                merged_segments.append(seg)

        if not merged_segments:
            merged_segments = [raw]

        # 4. Classify each chunk
        chunks: List[QueryChunk] = []
        for i, seg in enumerate(merged_segments, 1):
            seg_lower = seg.lower()
            intent_type = "conversational_inquiry"
            guidance = "Respond helpfully, articulately, and directly to the user's statement or question."

            # Check for math
            if any(op in seg_lower for op in ["plus", "minus", "times", "divided", "calculate", "+", "-", "*", "/"]) and any(c.isdigit() for c in seg):
                intent_type = "calculation"
                guidance = "Calculate arithmetic with mathematical accuracy."

            # Check for desktop automation request (open app, website, browser)
            elif (any(w in seg_lower for w in ["open", "launch", "start", "bring up", "browse to", "go to"]) and 
                  any(app in seg_lower for app in ["instagram", "youtube", "google", "github", "twitter", "linkedin", "browser", "notepad", "calculator", "calc", "tab", "website"])) or re.search(r'open\s+https?://', seg_lower):
                intent_type = "automation_request"
                guidance = "Confirm cheerfully and clearly that the requested website or application has been opened on the user's desktop."

            # Check for explicit user request to play game / take break
            elif any(g in seg_lower for g in ["play", "game", "2048", "pacman", "break", "rest", "distract"]) and any(w in seg_lower for w in ["play", "game", "2048", "pacman"]):
                intent_type = "action_request"
                guidance = "Acknowledge the user's explicit game request cheerfully and confirm launch."

            # Check for emotional expression
            elif any(e in seg_lower for e in ["stress", "exhaust", "tired", "burnout", "depress", "lonely", "sad", "feel down"]):
                intent_type = "emotional_support"
                guidance = "Offer sincere emotional validation, empathy, and warm comfort in MOMO's caring companion voice."

            # Check for web crawl / URL request
            elif re.findall(r'https?://[^\s]+', seg) or any(cw in seg_lower for cw in ["crawl", "scrape", "fetch url", "browse", "read link", "search web", "look up", "sih", "hackathon"]):
                intent_type = "web_crawl_request"
                guidance = "Extract, analyze, and synthesize authentic factual information from the crawled web resource or search. Deliver structured details without generic cheerleading."

            # Check for follow-up or information continuation
            elif any(w in seg_lower for w in ["tell me more", "more about", "tell more", "what else", "continue", "elaborate", "who else", "what about him", "what about her"]):
                intent_type = "follow_up_inquiry"
                guidance = "Elaborate in depth on the current subject or prior conversational context. Provide detailed, factual insights without asking generic questions."

            # Check for explanation / technical inquiry
            elif any(w in seg_lower for w in ["what is", "what are", "how does", "how do", "explain", "tell me about", "why is", "difference between"]) or any(e in seg_lower for e in entities):
                intent_type = "factual_inquiry"
                guidance = "Provide an accurate, articulate, well-structured explanation with clear real-world or code context."

            # Social greeting / banter
            elif any(w in seg_lower for w in ["hi", "hello", "hey", "how are you", "momo", "good morning"]):
                intent_type = "personal_banter"
                guidance = "Greet warmly and ask how you can help them today. Do NOT suggest playing games."

            # Find topics in this specific chunk
            chunk_topics = [e for e in entities if e in seg_lower]

            chunks.append(QueryChunk(
                chunk_id=i,
                text=seg,
                intent_type=intent_type,
                topics=chunk_topics,
                must_address=True,
                guidance=guidance
            ))

        # 5. Build structured LLM comprehension plan
        directive_lines = [
            "============================================================",
            "[BACKEND AGENT QUERY DECOMPOSITION & COMPREHENSION DIRECTIVE]",
            "The multi-agent system has parsed and chunked the user's input into discrete sub-goals:",
        ]
        for c in chunks:
            directive_lines.append(f"  - Chunk {c.chunk_id} [{c.intent_type.upper()}]: \"{c.text}\"")
            if c.guidance:
                directive_lines.append(f"    -> Directive: {c.guidance}")

        if detected_emotions:
            directive_lines.append(f"  - User Emotional Sentiment: {', '.join(detected_emotions).upper()}")
        if entities:
            directive_lines.append(f"  - Key Entities/Topics: {', '.join(entities)}")

        directive_lines.extend([
            "",
            "STRICT RESPONSE VERIFICATION CRITERIA:",
            "1. You MUST address EVERY individual chunk identified above. Do NOT ignore any part of the query.",
            "2. If an emotional chunk is present, comfort and validate the user's feelings first before diving into technical facts.",
            "3. If a technical or factual inquiry is present, ensure your explanation is rigorous, accurate, and concise.",
            "4. Never hallucinate knowledge cutoff dates or apologize for being an AI. Speak directly as MOMO.",
            "============================================================",
        ])

        comprehension_directive = "\n".join(directive_lines)

        all_urls = re.findall(r'https?://[^\s]+', raw)
        is_web_crawl = bool(all_urls) or any(c.intent_type == "web_crawl_request" for c in chunks)

        return {
            "original_query": raw,
            "chunks": [c.__dict__ for c in chunks],
            "primary_intent": chunks[0].intent_type if chunks else "general",
            "detected_emotions": detected_emotions,
            "entities": entities,
            "urls": all_urls,
            "is_web_crawl_request": is_web_crawl,
            "comprehension_directive": comprehension_directive,
        }

    @classmethod
    def verify_response_coverage(cls, decomposition: Dict[str, Any], generated_text: str) -> Dict[str, Any]:
        """
        Validates whether the generated response adequately addressed all query chunks.
        """
        chunks = decomposition.get("chunks", [])
        if not chunks or len(chunks) <= 1:
            return {"complete": True, "missing_chunks": []}

        gen_lower = generated_text.lower()
        missing = []

        for c in chunks:
            intent = c.get("intent_type")
            topics = c.get("topics", [])
            covered = False

            if intent == "emotional_support":
                # Check for empathy words
                if any(w in gen_lower for w in ["understand", "care", "proud", "breathe", "rest", "hard", "you're doing", "take care", "here for you", "stress"]):
                    covered = True
            elif intent == "factual_inquiry":
                # Check if topics or keywords from chunk were mentioned
                if topics and any(t.lower() in gen_lower for t in topics):
                    covered = True
                elif len(gen_lower.split()) > 15:
                    covered = True
            elif intent == "action_request":
                if any(w in gen_lower for w in ["game", "play", "break", "launch", "open", "let's"]):
                    covered = True
            else:
                covered = True

            if not covered:
                missing.append(c)

        return {
            "complete": len(missing) == 0,
            "missing_chunks": missing,
        }
