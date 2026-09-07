"""
Financial Insight validation schemas and checks.
"""
from typing import Dict, Any, Tuple
from .calculator import FinancialCalculator


class FinancialValidator:
    """
    Validates that financial records conform strictly to mathematical consistency.
    """

    @classmethod
    def validate_insight_dict(cls, data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], str]:
        if not data.get("invoice_number"):
            return False, data, "Missing invoice_number."

        try:
            total = float(data.get("invoice_total", 0.0))
            paid = float(data.get("amount_paid", 0.0))
        except (ValueError, TypeError):
            return False, data, "Invalid numeric values for invoice_total or amount_paid."

        if total < 0 or paid < 0:
            return False, data, "Financial figures cannot be negative."

        calculated_balance = FinancialCalculator.calculate_balance_due(total, paid)
        expected_status = FinancialCalculator.determine_payment_status(total, paid, data.get("due_date"))

        # Enforce deterministic mathematical truth
        data["invoice_total"] = round(total, 2)
        data["amount_paid"] = round(paid, 2)
        data["balance_due"] = calculated_balance
        data["payment_status"] = expected_status

        return True, data, "Validated successfully."
