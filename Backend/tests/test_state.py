"""
Unit tests for MomoState and merge reducer functions.
"""
import unittest
from graph.state import (
    MomoState,
    Message,
    ProcessedDocument,
    FinancialInsight,
    RetrievedChunk,
    HardwareCommand,
    MomoResponse,
    RoutingDecision,
)
from graph.reducers import (
    merge_messages,
    merge_documents,
    merge_financial_insights,
    merge_retrieved_context,
    merge_routing_decisions,
    merge_errors,
)


class TestStateAndReducers(unittest.TestCase):

    def test_message_reducers(self):
        m1 = Message(id="1", role="user", content="Hello MOMO")
        m2 = Message(id="2", role="assistant", content="Hey! How can I help?", expression="happy")
        merged = merge_messages([m1], [m2])
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0].content, "Hello MOMO")
        self.assertEqual(merged[1].content, "Hey! How can I help?")

        # Test deduplication/update
        m2_updated = Message(id="2", role="assistant", content="Updated response", expression="excited")
        merged2 = merge_messages(merged, [m2_updated])
        self.assertEqual(len(merged2), 2)
        self.assertEqual(merged2[1].content, "Updated response")
        self.assertEqual(merged2[1].expression, "excited")

    def test_document_reducers(self):
        d1 = ProcessedDocument(document_id="doc_1", filename="invoice1.pdf", text="Total: 100")
        d2 = ProcessedDocument(document_id="doc_2", filename="invoice2.pdf", text="Total: 200")
        merged = merge_documents([d1], [d2])
        self.assertEqual(len(merged), 2)

        # Update existing
        d1_mod = ProcessedDocument(document_id="doc_1", filename="invoice1.pdf", text="Total: 150")
        merged2 = merge_documents(merged, [d1_mod])
        self.assertEqual(len(merged2), 2)
        self.assertEqual(merged2[0].text, "Total: 150")

    def test_financial_insight_reducers(self):
        f1 = FinancialInsight(invoice_number="INV-01", invoice_total=1000, amount_paid=500, balance_due=500)
        f2 = FinancialInsight(invoice_number="INV-02", invoice_total=2500, amount_paid=2500, balance_due=0, payment_status="paid")
        merged = merge_financial_insights([f1], [f2])
        self.assertEqual(len(merged), 2)

        # Update
        f1_paid = FinancialInsight(invoice_number="INV-01", invoice_total=1000, amount_paid=1000, balance_due=0, payment_status="paid")
        merged2 = merge_financial_insights(merged, [f1_paid])
        self.assertEqual(len(merged2), 2)
        self.assertEqual(merged2[0].balance_due, 0)
        self.assertEqual(merged2[0].payment_status, "paid")

    def test_retrieved_context_reducers(self):
        c1 = RetrievedChunk(chunk_id="chk_1", document_id="doc_1", content="Chunk 1", score=0.92)
        c2 = RetrievedChunk(chunk_id="chk_2", document_id="doc_1", content="Chunk 2", score=0.85)
        merged = merge_retrieved_context([c1], [c2])
        self.assertEqual(len(merged), 2)

    def test_routing_decisions_reducers(self):
        r1 = RoutingDecision(supervisor="root", target_agent="conversation_supervisor", reason="Test 1")
        r2 = RoutingDecision(supervisor="conversation", target_agent="conversation_agent", reason="Test 2")
        merged = merge_routing_decisions([r1], [r2])
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0].supervisor, "root")
        self.assertEqual(merged[1].supervisor, "conversation")

    def test_error_reducers(self):
        errors = merge_errors(["Initial warning"], ["Initial warning", "New error"])
        self.assertEqual(len(errors), 2)

    def test_momo_state_instantiation(self):
        state = MomoState(
            messages=[Message(role="user", content="Test")],
            current_route="conversation",
            momo_expression="happy"
        )
        self.assertEqual(len(state.messages), 1)
        self.assertEqual(state.momo_expression, "happy")
        self.assertEqual(state.current_route, "conversation")


if __name__ == "__main__":
    unittest.main()
