"""
Relevance Analyzer Agent for MOMO.
Supervised post-processor for live web crawling and research results.
Filters out web noise, boilerplate, advertisements, and irrelevant search hits.
Scores candidate paragraphs and sentences for direct relevance to the user's specific query,
extracting key facts, figures, and direct answers for the local LLM to articulate.
"""
import re
import logging
from typing import Dict, Any, List, Tuple

from graph.state import MomoState, RetrievedChunk

logger = logging.getLogger(__name__)


class RelevanceAnalyzerAgent:
    """
    Analyzes raw crawled web content and extracts strictly relevant facts.
    """

    NOISE_PATTERNS = [
        re.compile(r"cookie\s+policy", re.IGNORECASE),
        re.compile(r"privacy\s+policy", re.IGNORECASE),
        re.compile(r"terms\s+of\s+(?:use|service)", re.IGNORECASE),
        re.compile(r"all\s+rights\s+reserved", re.IGNORECASE),
        re.compile(r"subscribe\s+(?:now|today)", re.IGNORECASE),
        re.compile(r"sign\s+in\s+to\s+read", re.IGNORECASE),
        re.compile(r"click\s+here\s+to", re.IGNORECASE),
        re.compile(r"newsletter\s+sign-?up", re.IGNORECASE),
        re.compile(r"advertisement", re.IGNORECASE),
        re.compile(r"share\s+on\s+(?:facebook|twitter|linkedin|whatsapp)", re.IGNORECASE),
    ]

    def __init__(self):
        pass

    @classmethod
    def clean_and_split_paragraphs(cls, text: str) -> List[str]:
        raw_paras = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n")]
        cleaned = []
        for p in raw_paras:
            p_clean = " ".join(p.split())
            # Skip very short fragments, navigation lines, or noise
            if len(p_clean) < 30:
                continue
            if any(pat.search(p_clean) for pat in cls.NOISE_PATTERNS):
                continue
            cleaned.append(p_clean)
        return cleaned

    @classmethod
    def score_relevance(cls, paragraph: str, query: str, query_tokens: List[str]) -> float:
        """
        Calculates a relevance score for a paragraph against query tokens.
        Considers keyword matching, numbers/dates, and density.
        """
        p_lower = paragraph.lower()
        score = 0.0

        # Exact phrase bonus
        if query.lower() in p_lower:
            score += 3.0

        # Token matches
        matched_tokens = 0
        for tok in query_tokens:
            if tok in p_lower:
                matched_tokens += 1
                score += 1.0

        if query_tokens:
            ratio = matched_tokens / len(query_tokens)
            score += ratio * 2.0

        # Numerical or factual detail bonus (dates, percentages, figures)
        if re.search(r"(?:19|20)\d{2}|\d+(?:%|st|nd|rd|th|km|crore|lakh|million|billion)", paragraph):
            score += 0.8

        # Penalty for overly generic text
        if len(paragraph) > 600:
            score *= 0.95

        return score

    async def run(self, state: MomoState) -> Dict[str, Any]:
        """
        Takes MomoState with retrieved_context, ranks and filters passages,
        and injects high-relevance factual excerpts into state.
        """
        last_user_msg = ""
        for m in reversed(state.messages):
            if m.role == "user":
                last_user_msg = m.content
                break

        if not last_user_msg:
            last_user_msg = state.voice_input or ""

        raw_chunks = state.retrieved_context or []
        if not raw_chunks:
            logger.info("RelevanceAnalyzerAgent: No retrieved chunks to analyze.")
            return {"current_agent": "relevance_analyzer_agent"}

        logger.info(f"RelevanceAnalyzerAgent evaluating {len(raw_chunks)} chunks for query: '{last_user_msg}'")

        # Extract meaningful query keywords (excluding stop words)
        stop_words = {
            "what", "is", "the", "a", "an", "of", "and", "or", "in", "on", "at", "to", "for",
            "with", "about", "tell", "me", "show", "give", "crawl", "web", "search", "google",
            "explain", "how", "why", "who", "when", "where", "please", "can", "you", "go"
        }
        tokens = [
            w.lower() for w in re.sub(r"[^\w\s]", "", last_user_msg).split()
            if len(w) > 2 and w.lower() not in stop_words
        ]

        scored_passages: List[Tuple[float, str, str, str]] = []  # (score, text, source, url)

        for chunk in raw_chunks:
            source = chunk.metadata.get("source", "Web Resource") if chunk.metadata else "Web Resource"
            url = chunk.metadata.get("url", "") if chunk.metadata else ""
            paragraphs = self.clean_and_split_paragraphs(chunk.content)

            for p in paragraphs:
                score = self.score_relevance(p, last_user_msg, tokens)
                if score > 0.5:
                    scored_passages.append((score, p, source, url))

        # Sort descending by relevance score
        scored_passages.sort(key=lambda x: x[0], reverse=True)

        # Select top substantive passages
        selected = scored_passages[:5]

        if not selected and raw_chunks:
            # Fallback: take clean paragraphs from the first chunk
            for chunk in raw_chunks[:2]:
                paras = self.clean_and_split_paragraphs(chunk.content)
                for p in paras[:2]:
                    selected.append((1.0, p, chunk.metadata.get("source", "Web"), chunk.metadata.get("url", "")))

        # Build refined RetrievedChunk items
        filtered_chunks: List[RetrievedChunk] = []
        key_facts: List[str] = []

        for idx, (sc, text, src, url) in enumerate(selected, 1):
            filtered_chunks.append(RetrievedChunk(
                chunk_id=f"relevant-{idx}",
                document_id=f"fact-{idx}",
                content=text,
                score=round(min(1.0, sc / 5.0), 3),
                metadata={"url": url, "source": src, "relevance_score": sc}
            ))
            # Extract first sentence or bullet
            first_sent = text.split(". ")[0].strip() + "."
            key_facts.append(f"• ({src}) {first_sent}")

        # Assemble high-clarity supervisor directive for ConversationAgent / LLM
        facts_summary = "\n".join(key_facts[:5])
        passages_summary = "\n\n".join(f"[{c.metadata.get('source', 'Web')}]: {c.content}" for c in filtered_chunks[:3])
        directive = (
            f"[RELEVANCE-FILTERED WEB RESEARCH ({len(filtered_chunks)} verified passages)]:\n"
            f"User Target Query: \"{last_user_msg}\"\n\n"
            f"KEY EXTRACTED FACTS:\n{facts_summary}\n\n"
            f"DETAILED PASSAGES:\n{passages_summary}\n\n"
            "DIRECTIVE FOR LLM: Directly answer the user's specific inquiry using these verified factual excerpts. "
            "Focus specifically on the core subject requested. "
            "Never reply with generic cheerleading, filler comments, or game suggestions."
        )

        metadata = dict(state.metadata or {})
        metadata["key_facts"] = key_facts
        metadata["facts_summary"] = facts_summary
        metadata["source_urls"] = [c.metadata.get("url") for c in filtered_chunks if c.metadata.get("url")]

        logger.info(f"RelevanceAnalyzerAgent selected {len(filtered_chunks)} relevant facts.")
        return {
            "retrieved_context": filtered_chunks,
            "conversation_context": directive,
            "metadata": metadata,
            "current_agent": "relevance_analyzer_agent"
        }
