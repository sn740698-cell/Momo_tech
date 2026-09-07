"""
Unit tests for deterministic financial calculations and validations.
"""
import unittest
from datetime import date, timedelta
from finance.calculator import FinancialCalculator
from finance.validators import FinancialValidator
from finance.extractor import FinancialExtractor


class TestFinanceEngine(unittest.TestCase):

    def test_balance_due_calculation(self):
        # Exact subtraction
        self.assertEqual(FinancialCalculator.calculate_balance_due(48500, 20000), 28500.0)
        self.assertEqual(FinancialCalculator.calculate_balance_due(100.50, 50.25), 50.25)
        
        # Paid greater than or equal to total returns 0
        self.assertEqual(FinancialCalculator.calculate_balance_due(100, 150), 0.0)
        self.assertEqual(FinancialCalculator.calculate_balance_due(500, 500), 0.0)

    def test_payment_status_determination(self):
        # Fully paid
        self.assertEqual(FinancialCalculator.determine_payment_status(1000, 1000), "paid")
        self.assertEqual(FinancialCalculator.determine_payment_status(0, 0), "paid")

        # Partially paid
        self.assertEqual(FinancialCalculator.determine_payment_status(1000, 250), "partially_paid")

        # Unpaid
        self.assertEqual(FinancialCalculator.determine_payment_status(1000, 0), "unpaid")

        # Overdue
        past_date = (date.today() - timedelta(days=10)).strftime("%Y-%m-%d")
        self.assertEqual(FinancialCalculator.determine_payment_status(1000, 200, past_date), "overdue")

        # Future due date not overdue
        future_date = (date.today() + timedelta(days=10)).strftime("%Y-%m-%d")
        self.assertEqual(FinancialCalculator.determine_payment_status(1000, 200, future_date), "partially_paid")

    def test_financial_validator(self):
        valid, data, msg = FinancialValidator.validate_insight_dict({
            "invoice_number": "INV-1042",
            "invoice_total": 48500,
            "amount_paid": 20000,
            "currency": "INR",
        })
        self.assertTrue(valid)
        self.assertEqual(data["balance_due"], 28500.0)
        self.assertEqual(data["payment_status"], "partially_paid")

    def test_financial_extractor(self):
        sample_invoice_text = """
        INVOICE #INV-8899
        Acme Software Consulting
        Invoice Date: 2026-08-01
        Due Date: 2026-09-30
        Total Amount: ₹75,000.00
        Amount Paid: ₹25,000.00
        """
        extracted = FinancialExtractor.extract_from_text(sample_invoice_text)
        self.assertEqual(extracted["invoice_number"], "INV-8899")
        self.assertEqual(extracted["invoice_total"], 75000.0)
        self.assertEqual(extracted["amount_paid"], 25000.0)
        self.assertEqual(extracted["balance_due"], 50000.0)
        self.assertEqual(extracted["payment_status"], "partially_paid")
        self.assertEqual(extracted["currency"], "INR")


if __name__ == "__main__":
    unittest.main()
