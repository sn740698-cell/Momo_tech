"""
Fact Verifier Agent for MOMO.
Specializes in multi-source fact cross-verification, consensus scoring,
noise and boilerplate elimination, and data integrity validation.
"""
import re
import logging
from typing import Dict, Any, List, Set

from graph.state import MomoState, RetrievedChunk

logger = logging.getLogger(__name__)


class FactVerifierAgent:
    """
    Third stage of the Web Crawling Multi-Agent Squad.
    Consumes scraped web articles, eliminates residual web noise (cookie banners,
    paywall text, navigation disclaimers), cross-verifies shared facts across domains,
    and assigns consensus confidence scores to factual statements.
    """

    NOISE_PATTERNS = [
        r"cookie\s+policy",
        r"subscribe\s+now",
        r"all\s+rights\s+reserved",
        r"terms\s+of\s+service",
        r"privacy\s+notice",
        r"sign\s+in\s+to\s+continue",
        r"unlock\s+with\s+subscription",
        r"advertisement",
        r"share\s+this\s+article",
    ]

    @classmethod
    def clean_text_noise(cls, text: str) -> str:
        """Removes residual advertising, boilerplate, and cookie notices."""
        if not text:
            return ""
        lines = text.splitlines()
        cleaned_lines = []
        for line in lines:
            line_str = line.strip()
            if len(line_str) < 15:
                continue
            if any(re.search(pat, line_str, re.IGNORECASE) for pat in cls.NOISE_PATTERNS):
                continue
            cleaned_lines.append(line_str)
        return "\n".join(cleaned_lines)

    async def run(self, state: MomoState) -> Dict[str, Any]:
        scraped_chunks = state.retrieved_context or []
        if not scraped_chunks:
            logger.info("FactVerifierAgent: No chunks to verify.")
            return {"current_agent": "fact_verifier_agent"}

        logger.info(f"FactVerifierAgent cross-verifying facts across {len(scraped_chunks)} sources...")

        verified_chunks: List[RetrievedChunk] = []
        all_terms: Set[str] = set()

        for ch in scraped_chunks:
            cleaned = self.clean_text_noise(ch.content)
            if not cleaned or len(cleaned) < 40:
                continue

            # Extract key nouns/entities
            words = set(w.lower() for w in re.findall(r"\b[A-Za-z0-9\-_]{4,}\b", cleaned))
            consensus_overlap = len(words.intersection(all_terms))
            all_terms.update(words)

            # Consensus bonus: if facts share key terms with other sources
            consensus_score = min(1.0, ch.score + (0.05 * min(consensus_overlap, 4)))

            verified_chunks.append(RetrievedChunk(
                chunk_id=f"verified-{len(verified_chunks) + 1}",
                document_id=ch.document_id,
                content=cleaned,
                score=round(consensus_score, 3),
                metadata={
                    **ch.metadata,
                    "stage": "verified",
                    "consensus_overlap": consensus_overlap
                }
            ))

        logger.info(f"FactVerifierAgent verified {len(verified_chunks)} passages with consensus scoring.")

        return {
            "retrieved_context": verified_chunks,
            "current_agent": "fact_verifier_agent"
        }
