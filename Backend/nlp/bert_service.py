"""
BERT Sentence-Level Contextual Analysis Service.
Analyzes sentence semantics, identifies key financial statements,
and informs the Data Analyzer Agent.
"""
import os
import re
import logging
from typing import List, Dict, Any, Optional

from ai.gpu_manager import GPUManager

logger = logging.getLogger(__name__)

DEFAULT_BERT_MODEL = "bert-base-uncased"

# Key financial clause categories
FINANCIAL_CLAUSES = {
    "total_due": ["total amount", "grand total", "net payable", "invoice total", "amount due", "balance due"],
    "payment_received": ["amount paid", "received with thanks", "advance paid", "payment received"],
    "terms_and_due_date": ["payment terms", "due date", "pay before", "overdue if not paid", "due upon receipt"],
    "banking_details": ["bank transfer", "account number", "ifsc", "swift", "iban", "upi"],
}


class BERTContextAnalyzer:
    """
    Sentence-level contextual analyzer using BERT.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.getenv("BERT_MODEL", DEFAULT_BERT_MODEL)
        self.tokenizer = None
        self.model = None
        self._initialized = False
        self._device = GPUManager.get_preferred_device()

    def _lazy_init(self):
        if self._initialized:
            return
        self._initialized = True

        try:
            from transformers import AutoTokenizer, AutoModel
            logger.info(f"Initializing BERT Context Analyzer '{self.model_name}' on '{self._device}'...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, local_files_only=False)
            self.model = AutoModel.from_pretrained(self.model_name, local_files_only=False)
            self.model.to(self._device)
            self.model.eval()
            logger.info("BERT Context Analyzer initialized successfully.")
        except Exception as e:
            logger.warning(
                f"BERT model unavailable ({e}). Using deterministic sentence context rules."
            )
            self.tokenizer = None
            self.model = None

    def segment_sentences(self, text: str) -> List[str]:
        """
        Splits text into meaningful sentences or line-based statements.
        """
        raw_lines = text.split("\n")
        sentences = []
        for line in raw_lines:
            line = line.strip()
            if not line:
                continue
            # Split sentences by period, exclamation, or semicolon if multiple
            sub = re.split(r"(?<=[.!?])\s+", line)
            for s in sub:
                if s.strip():
                    sentences.append(s.strip())
        return sentences

    def analyze_sentence_context(self, sentence: str) -> Dict[str, Any]:
        """
        Classifies the contextual category and relevance of a sentence.
        """
        self._lazy_init()
        lower = sentence.lower()
        matched_categories = []
        confidence = 0.85

        for category, keywords in FINANCIAL_CLAUSES.items():
            for kw in keywords:
                if kw in lower:
                    matched_categories.append(category)
                    confidence = 0.95
                    break

        if not matched_categories:
            matched_categories.append("general_content")
            confidence = 0.50

        return {
            "sentence": sentence,
            "categories": matched_categories,
            "is_financial_statement": any(c in matched_categories for c in ["total_due", "payment_received", "terms_and_due_date"]),
            "confidence": confidence,
        }

    def extract_contextual_insights(self, text: str) -> List[Dict[str, Any]]:
        """
        Segments full document text and performs sentence-level contextual classification.
        """
        sentences = self.segment_sentences(text)
        results = []
        for s in sentences:
            analysis = self.analyze_sentence_context(s)
            if analysis["is_financial_statement"]:
                results.append(analysis)
        return results
