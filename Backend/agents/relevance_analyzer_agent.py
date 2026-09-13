"""
Relevance Analyzer Agent for MOMO.
Supervised post-processor for live web crawling and research results.
Filters out web noise, boilerplate, advertisements, and irrelevant search hits.
Scores candidate paragraphs and sentences for direct relevance to the user's specific query,
extracting key facts, figures, and direct answers for the local LLM to articulate.
"""
import re
import math
import logging
from typing import Dict, Any, List, Tuple, Optional

from graph.state import MomoState, RetrievedChunk
from ai_workflow.services.web_crawler_service import LiveWebCrawlerService

logger = logging.getLogger(__name__)


class BM25PassageRanker:
    """
    Mathematical BM25 passage ranking engine.
    Calculates TF-IDF BM25 relevance scores for document passages against user queries.
    Uses safe Lucene IDF floor to guarantee positive, balanced IDF across passage sets.
    """
    def __init__(self, tokenized_passages: List[List[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus = tokenized_passages
        self.corpus_size = len(tokenized_passages)
        self.avg_doc_len = sum(len(d) for d in tokenized_passages) / max(1, self.corpus_size)
        self.doc_freqs: Dict[str, int] = {}
        for doc in tokenized_passages:
            for w in set(doc):
                self.doc_freqs[w] = self.doc_freqs.get(w, 0) + 1

        # Lucene BM25 IDF: ln(1 + (N - n + 0.5) / (n + 0.5))
        self.idf: Dict[str, float] = {}
        for w, freq in self.doc_freqs.items():
            self.idf[w] = math.log(1.0 + (self.corpus_size - freq + 0.5) / (freq + 0.5))

    def get_scores(self, query_tokens: List[str]) -> List[float]:
        scores = [0.0] * self.corpus_size
        for i, doc in enumerate(self.corpus):
            doc_len = len(doc)
            doc_counts: Dict[str, int] = {}
            for w in doc:
                doc_counts[w] = doc_counts.get(w, 0) + 1

            score = 0.0
            for q in query_tokens:
                if q in doc_counts:
                    freq = doc_counts[q]
                    idf_val = self.idf.get(q, 0.5)
                    tf = (freq * (self.k1 + 1.0)) / (freq + self.k1 * (1.0 - self.b + self.b * (doc_len / max(1.0, self.avg_doc_len))))
                    score += idf_val * tf
            scores[i] = score
        return scores


class RelevanceAnalyzerAgent:
    """
    Analyzes raw crawled web content, applies BM25 passage ranking,
    and extracts strictly relevant, verified facts to eliminate LLM hallucinations.
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
    def extract_first_sentence(cls, text: str) -> str:
        """Extracts the first complete sentence while preserving initials and honorifics."""
        if not text:
            return ""
        protected = re.sub(r'\b([A-Z])\.\s*', r'\1<DOT_INITIAL> ', text)
        protected = re.sub(r'\b(Dr|Mr|Mrs|Ms|Prof|Sr|Jr|vs|eg|ie)\.\s*', r'\1<DOT_ABBR> ', protected, flags=re.IGNORECASE)
        parts = re.split(r'[.!?]\s+', protected)
        if parts:
            first = parts[0].replace('<DOT_INITIAL>', '.').replace('<DOT_ABBR>', '.').strip()
            if not first.endswith('.'):
                first += '.'
            return first
        return text.strip()

    @classmethod
    def clean_and_split_passages(cls, text: str) -> List[str]:
        """
        Cleans, infobox-sanitizes, and splits text into cohesive 2-4 sentence passages.
        """
        sanitized = LiveWebCrawlerService.sanitize_tables_and_infoboxes(text)
        raw_paras = [p.strip() for p in sanitized.replace("\r\n", "\n").split("\n\n")]
        passages: List[str] = []

        for p in raw_paras:
            p_clean = " ".join(p.split()).replace("\u2191", " ").replace("^", " ")
            p_clean = re.sub(r'\[\d+\]', '', p_clean).strip()
            if len(p_clean) < 25:
                continue
            if any(pat.search(p_clean) for pat in cls.NOISE_PATTERNS):
                continue

            # If paragraph is long, split into 2-3 sentence cohesive chunks
            if len(p_clean) > 400:
                protected = re.sub(r'\b([A-Z])\.\s*', r'\1<DOT_INITIAL> ', p_clean)
                protected = re.sub(r'\b(Dr|Mr|Mrs|Ms|Prof|Sr|Jr|vs|eg|ie)\.\s*', r'\1<DOT_ABBR> ', protected, flags=re.IGNORECASE)
                sentences = [
                    s.replace('<DOT_INITIAL>', '.').replace('<DOT_ABBR>', '.').strip()
                    for s in re.split(r'[.!?]\s+', protected) if s.strip()
                ]
                cur_chunk: List[str] = []
                cur_len = 0
                for s_str in sentences:
                    cur_chunk.append(s_str)
                    cur_len += len(s_str)
                    if cur_len >= 220:
                        passages.append(" ".join(cur_chunk))
                        cur_chunk = []
                        cur_len = 0
                if cur_chunk:
                    passages.append(" ".join(cur_chunk))
            else:
                passages.append(p_clean)

        return passages

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        """Normalizes and extracts lowercase word tokens."""
        return [
            w.lower().strip(".,()[]{}:;\"'!?")
            for w in re.sub(r"[^\w\s-]", " ", text).split()
            if len(w) > 1
        ]

    async def run(self, state: MomoState) -> Dict[str, Any]:
        """
        Takes MomoState with retrieved_context, ranks passages with BM25,
        filters noise, and injects strictly verified factual excerpts into state.
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

        # Normalize query and extract meaningful keywords (excluding conversational stop words)
        clean_q = LiveWebCrawlerService.expand_query(last_user_msg)
        stop_words = {
            "what", "is", "the", "a", "an", "of", "and", "or", "in", "on", "at", "to", "for",
            "with", "about", "tell", "me", "show", "give", "crawl", "web", "search", "google",
            "explain", "how", "why", "who", "when", "where", "please", "can", "you", "go", "its"
        }
        query_tokens = [
            w for w in self.tokenize(clean_q)
            if len(w) > 2 and w not in stop_words
        ]
        if not query_tokens:
            query_tokens = [w for w in self.tokenize(last_user_msg) if len(w) > 2 and w not in stop_words]

        # Incorporate resolved topic tokens from conversation memory so follow-up queries rank properly
        active_topic = state.metadata.get("active_topic") if state.metadata else None
        if active_topic:
            topic_tokens = [w for w in self.tokenize(active_topic) if len(w) > 2 and w not in stop_words]
            query_tokens = list(dict.fromkeys(query_tokens + topic_tokens))

        # Extract all candidate passages across chunks
        candidate_pool: List[Tuple[str, str, str]] = []  # (passage_text, source, url)
        for chunk in raw_chunks:
            source = chunk.metadata.get("source", "Web Resource") if chunk.metadata else "Web Resource"
            url = chunk.metadata.get("url", "") if chunk.metadata else ""
            passages = self.clean_and_split_passages(chunk.content)
            for p in passages:
                candidate_pool.append((p, source, url))

        if not candidate_pool:
            logger.info("RelevanceAnalyzerAgent: No candidate passages extracted.")
            return {"current_agent": "relevance_analyzer_agent"}

        # Tokenize passages for BM25
        tokenized_corpus = [self.tokenize(p[0]) for p in candidate_pool]
        bm25_ranker = BM25PassageRanker(tokenized_corpus)
        bm25_scores = bm25_ranker.get_scores(query_tokens)

        # Combine BM25 with Exact Phrase and Entity / Numerical Detail Bonuses
        scored_passages: List[Tuple[float, str, str, str]] = []
        clean_q_lower = clean_q.lower()

        for (p_text, src, url), bm_sc in zip(candidate_pool, bm25_scores):
            p_lower = p_text.lower()
            combined_score = bm_sc

            # 1. Exact phrase or entity subject match bonus
            clean_phrase = re.sub(r'[^\w\s]', '', clean_q_lower).strip()
            p_clean_text = re.sub(r'[^\w\s]', '', p_lower)
            if clean_q_lower in p_lower or (len(clean_phrase) > 4 and clean_phrase in p_clean_text):
                combined_score += 3.0

            # 2. Token overlap ratio
            matched = sum(1 for q in query_tokens if q in p_lower)
            if query_tokens:
                combined_score += (matched / len(query_tokens)) * 2.0

            # 3. Numerical or factual detail bonus (dates, figures, awards)
            if re.search(r"\b(?:19|20)\d{2}\b|\b\d+(?:%|st|nd|rd|th|km|crore|lakh|million|billion)\b", p_text):
                combined_score += 0.8

            # Only retain passages with non-zero query alignment
            if combined_score > 0.3:
                scored_passages.append((combined_score, p_text, src, url))

        # Sort descending by combined relevance score
        scored_passages.sort(key=lambda x: x[0], reverse=True)

        # Select top substantive passages (up to 5)
        selected = scored_passages[:5]

        if not selected and candidate_pool:
            # Fallback: select passages containing any query token
            for p_text, src, url in candidate_pool:
                p_lower = p_text.lower()
                if any(q in p_lower for q in query_tokens):
                    selected.append((1.0, p_text, src, url))
                    if len(selected) >= 3:
                        break

        # Build refined RetrievedChunk items
        filtered_chunks: List[RetrievedChunk] = []
        key_facts: List[str] = []

        for idx, (sc, text, src, url) in enumerate(selected, 1):
            filtered_chunks.append(RetrievedChunk(
                chunk_id=f"bm25-{idx}",
                document_id=f"fact-{idx}",
                content=text,
                score=round(min(1.0, sc / 5.0), 3),
                metadata={"url": url, "source": src, "relevance_score": sc, "algorithm": "BM25+Entity"}
            ))
            # Extract first sentence safely without splitting on initials
            first_sent = self.extract_first_sentence(text)
            key_facts.append(f"• ({src}) {first_sent}")

        facts_summary = "\n".join(key_facts[:5])
        passages_summary = "\n\n".join(f"[{c.metadata.get('source', 'Web')}]: {c.content}" for c in filtered_chunks[:4])

        directive = (
            f"[BM25-FILTERED VERIFIED RESEARCH ({len(filtered_chunks)} authoritative passages)]:\n"
            f"User Target Subject: \"{clean_q}\"\n\n"
            f"KEY EXTRACTED FACTS:\n{facts_summary}\n\n"
            f"VERIFIED CONTEXT PASSAGES:\n{passages_summary}\n\n"
            "DIRECTIVE FOR LLM: Directly answer the user's specific inquiry using ONLY these verified factual excerpts. "
            "Format the key information into clean, distinct bullet points (• ). "
            "Never invent outside dates, movies, or achievements that are not confirmed above. "
            "Never reply with generic cheerleading, filler comments, or game suggestions."
        )

        metadata = dict(state.metadata or {})
        metadata["key_facts"] = key_facts
        metadata["facts_summary"] = facts_summary
        metadata["source_urls"] = [c.metadata.get("url") for c in filtered_chunks if c.metadata.get("url")]

        logger.info(f"RelevanceAnalyzerAgent successfully selected {len(filtered_chunks)} BM25-ranked facts.")
        return {
            "retrieved_context": filtered_chunks,
            "conversation_context": directive,
            "metadata": metadata,
            "current_agent": "relevance_analyzer_agent"
        }
