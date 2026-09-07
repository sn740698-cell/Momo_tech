"""
Data Analyzer Agent for MOMO.
Analyzes invoice and document information, performs verified calculations,
and populates structured FinancialInsight objects in state.
"""
import logging
from typing import Dict, Any, List

from graph.state import MomoState, FinancialInsight
from finance.calculator import FinancialCalculator
from finance.extractor import FinancialExtractor
from nlp.bert_service import BERTContextAnalyzer

logger = logging.getLogger(__name__)


class DataAnalyzerAgent:
    """
    Produces deterministic, structured financial data without generative hallucination.
    """

    def __init__(self):
        self.bert = BERTContextAnalyzer()

    async def run(self, state: MomoState) -> Dict[str, Any]:
        updated_insights: List[FinancialInsight] = []

        # 1. Re-verify any existing financial insights in state
        for fi in state.financial_insights:
            verified_balance = FinancialCalculator.calculate_balance_due(fi.invoice_total, fi.amount_paid)
            verified_status = FinancialCalculator.determine_payment_status(
                fi.invoice_total, fi.amount_paid, fi.due_date
            )
            updated_insights.append(FinancialInsight(
                invoice_number=fi.invoice_number,
                invoice_total=fi.invoice_total,
                amount_paid=fi.amount_paid,
                balance_due=verified_balance,
                currency=fi.currency,
                due_date=fi.due_date,
                payment_status=verified_status,
                confidence=1.0,
                line_items=fi.line_items,
                notes=fi.notes
            ))

        # 2. If documents were ingested without insights yet, analyze their text
        for doc in state.documents:
            already_analyzed = any(i.invoice_number == doc.metadata.get("invoice_number") for i in updated_insights)
            if not already_analyzed and doc.text:
                extracted = FinancialExtractor.extract_from_text(doc.text)
                if extracted and extracted.get("invoice_total", 0) > 0:
                    updated_insights.append(FinancialInsight(**extracted))

        # 3. Analyze retrieved context chunks for financial figures if needed
        if not updated_insights and state.retrieved_context:
            combined_chunk_text = "\n".join(c.content for c in state.retrieved_context)
            extracted = FinancialExtractor.extract_from_text(combined_chunk_text)
            if extracted and extracted.get("invoice_total", 0) > 0:
                updated_insights.append(FinancialInsight(**extracted))

        logger.info(f"DataAnalyzerAgent verified {len(updated_insights)} financial insights.")
        return {
            "financial_insights": updated_insights,
            "current_agent": "data_analyzer_agent"
        }
