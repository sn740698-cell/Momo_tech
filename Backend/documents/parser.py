"""
Document text parser for text files, markdown, and PDFs.
"""
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DocumentParser:
    """
    Extracts text content from various file formats.
    """

    @classmethod
    def parse_bytes(cls, content: bytes, filename: str) -> str:
        ext = filename.lower().split(".")[-1] if "." in filename else "txt"

        if ext in ("txt", "md", "json", "csv"):
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                return content.decode("latin-1", errors="ignore")

        elif ext == "pdf":
            return cls._parse_pdf(content)

        # Fallback
        try:
            return content.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    @classmethod
    def _parse_pdf(cls, content: bytes) -> str:
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(content))
            pages = []
            for p in reader.pages:
                text = p.extract_text() or ""
                pages.append(text)
            return "\n\n".join(pages)
        except ImportError:
            pass

        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=content, filetype="pdf")
            pages = [page.get_text() for page in doc]
            return "\n\n".join(pages)
        except ImportError:
            pass

        # If no PDF library installed, attempt ascii/utf-8 text extraction
        logger.warning("No PDF parser library (pypdf/fitz) found. Attempting raw text extraction.")
        return content.decode("latin-1", errors="ignore")
