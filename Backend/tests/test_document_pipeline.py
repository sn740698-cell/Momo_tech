"""
Integration tests for Document Processing, BERT Analysis, and ChromaDB Retrieval.
"""
import unittest
from documents.processor import DocumentProcessor
from retrieval.retriever import DocumentRetriever
from documents.chunker import DocumentChunker


class TestDocumentPipeline(unittest.TestCase):

    def setUp(self):
        self.processor = DocumentProcessor()
        self.retriever = DocumentRetriever()

    def test_chunker(self):
        sample_text = (
            "Paragraph one is introducing the document.\n\n"
            "Paragraph two contains important details about billing and payment terms. "
            "Please ensure invoices are cleared within 30 days of receipt.\n\n"
            "Paragraph three covers contact information and support channels."
        )
        chunks = DocumentChunker.chunk_text(sample_text, chunk_size=100, chunk_overlap=10)
        self.assertGreater(len(chunks), 1)

    def test_document_processor_and_retrieval(self):
        invoice_content = b"""
        INVOICE #INV-5522
        Client: Stark Industries
        Total Due: $15,000.00
        Amount Paid: $5,000.00
        Payment Due Date: 2026-10-15
        Terms: Net 30 days. Wire transfer details provided below.
        """
        doc, insight, extra = self.processor.process_document(
            content=invoice_content,
            filename="stark_invoice.txt",
            document_id="doc_stark_55"
        )

        self.assertEqual(doc.document_id, "doc_stark_55")
        self.assertEqual(doc.processing_status, "completed")
        self.assertIsNotNone(insight)
        self.assertEqual(insight.invoice_number, "INV-5522")
        self.assertEqual(insight.balance_due, 10000.0)
        self.assertEqual(insight.payment_status, "partially_paid")

        # Test semantic retrieval
        retrieved = self.retriever.retrieve_context("What is the payment due date?", top_k=2, similarity_threshold=0.0)
        self.assertTrue(len(retrieved) > 0)
        self.assertIn("content", retrieved[0])


if __name__ == "__main__":
    unittest.main()
