"""
Deterministic Financial Calculations Engine.
Strict mathematical source-of-truth for invoices, receipts, and payments.
Never delegates arithmetic to generative LLMs.
"""
from typing import Optional, Dict, Any
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


class FinancialCalculator:
    """
    Guarantees mathematically verified financial calculations.
    """

    @staticmethod
    def calculate_balance_due(total: float, paid: float) -> float:
        """
        Calculates balance due = total - paid.
        Enforces 2 decimal precision and non-negative values.
        """
        total = round(float(total), 2)
        paid = round(float(paid), 2)
        balance = round(total - paid, 2)
        return max(0.0, balance)

    @staticmethod
    def determine_payment_status(total: float, paid: float, due_date_str: Optional[str] = None) -> str:
        """
        Determines deterministic status: 'paid', 'partially_paid', 'unpaid', 'overdue'.
        """
        total = round(float(total), 2)
        paid = round(float(paid), 2)
        balance = round(total - paid, 2)

        if total <= 0:
            return "paid"

        if balance <= 0.0:
            return "paid"

        # Check if overdue
        is_overdue = False
        if due_date_str:
            try:
                # Try parsing standard formats: YYYY-MM-DD or DD/MM/YYYY
                d_date = None
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
                    try:
                        d_date = datetime.strptime(due_date_str.strip(), fmt).date()
                        break
                    except ValueError:
                        continue

                if d_date and d_date < date.today():
                    is_overdue = True
            except Exception as e:
                logger.debug(f"Error checking due date '{due_date_str}': {e}")

        if is_overdue:
            return "overdue"

        if paid > 0:
            return "partially_paid"

        return "unpaid"

    @classmethod
    def compute_insight(
        cls,
        invoice_number: str,
        invoice_total: float,
        amount_paid: float,
        currency: str = "INR",
        due_date: Optional[str] = None,
        line_items: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Produces a validated financial insight dictionary.
        """
        total = round(float(invoice_total), 2)
        paid = round(float(amount_paid), 2)
        balance = cls.calculate_balance_due(total, paid)
        status = cls.determine_payment_status(total, paid, due_date)

        return {
            "invoice_number": invoice_number.strip(),
            "invoice_total": total,
            "amount_paid": paid,
            "balance_due": balance,
            "currency": currency.upper().strip() if currency else "INR",
            "due_date": due_date.strip() if due_date else None,
            "payment_status": status,
            "confidence": 1.0,
            "line_items": line_items or [],
        }
