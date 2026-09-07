"""
Financial Field Extractor.
Extracts invoice figures, dates, and identifiers from text and passes
to deterministic calculator.
"""
import re
from typing import Dict, Any, Optional, List
from .calculator import FinancialCalculator


class FinancialExtractor:
    """
    Extracts financial fields from document text using contextual patterns.
    """

    INVOICE_NUM_PATTERNS = [
        r"(?:invoice|inv|bill|receipt|ref|reference)\s*(?:no\.?|#|number|id)?[:\s-]*([A-Z0-9_-]{3,20})",
        r"#\s*([A-Z0-9_-]{3,15})",
    ]

    TOTAL_PATTERNS = [
        r"(?:grand\s+total|total\s+amount|invoice\s+total|total\s+due|net\s+total|total)\s*[:\s₹$€£Rs.]*([0-9,]+(?:\.[0-9]{1,2})?)",
    ]

    PAID_PATTERNS = [
        r"(?:amount\s+paid|paid\s+amount|paid|advance|received)\s*[:\s₹$€£Rs.]*([0-9,]+(?:\.[0-9]{1,2})?)",
    ]

    BALANCE_PATTERNS = [
        r"(?:balance\s+due|remaining\s+balance|amount\s+due|balance|due\s+amount)\s*[:\s₹$€£Rs.]*([0-9,]+(?:\.[0-9]{1,2})?)",
    ]

    DUE_DATE_PATTERNS = [
        r"(?:due\s+date|payment\s+due|due\s+by|pay\s+before)\s*[:\s-]*([0-9]{4}[-/][0-9]{2}[-/][0-9]{2}|[0-9]{2}[-/][0-9]{2}[-/][0-9]{4})",
    ]

    CURRENCY_PATTERNS = [
        (r"(?:₹|INR|Rs\.?|Rupees)", "INR"),
        (r"(?:\$|USD|Dollars)", "USD"),
        (r"(?:€|EUR|Euros)", "EUR"),
        (r"(?:£|GBP|Pounds)", "GBP"),
    ]

    @classmethod
    def clean_number(cls, raw_val: str) -> float:
        cleaned = raw_val.replace(",", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    @classmethod
    def extract_from_text(cls, text: str) -> Dict[str, Any]:
        """
        Extracts financial elements and calculates verified balance.
        """
        lines = text.split("\n")
        invoice_no = "INV-UNKNOWN"
        for pat in cls.INVOICE_NUM_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                invoice_no = match.group(1).strip()
                break

        # Extract currency
        currency = "INR"
        for pat, curr in cls.CURRENCY_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                currency = curr
                break

        # Extract total
        total = 0.0
        for pat in cls.TOTAL_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                total = cls.clean_number(match.group(1))
                break

        # Extract amount paid
        paid = 0.0
        for pat in cls.PAID_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                paid = cls.clean_number(match.group(1))
                break

        # Extract explicit balance if mentioned, otherwise compute
        due_date = None
        for pat in cls.DUE_DATE_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                due_date = match.group(1).strip()
                break

        # Always use the deterministic calculator for balance and status
        insight = FinancialCalculator.compute_insight(
            invoice_number=invoice_no,
            invoice_total=total,
            amount_paid=paid,
            currency=currency,
            due_date=due_date
        )

        return insight
