"""PDF ingestion pipeline.

Extracts text with ``pypdf`` (lightweight, pure-Python — keeps the image well
under Render's 512 MB free-tier RAM limit). Pages with no embedded text layer
(scanned PDFs) are sent through OCR in :mod:`src.ocr` when ``OCR_ENABLED=true``.

Replaces the previous Docling stack, which pulled in a large ML dependency
footprint that risked OOM crashes on Render's free tier.
"""

from __future__ import annotations

import io
import logging

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from src.config import get_settings
from src.ocr import extract_text_from_pdf_page

logger = logging.getLogger(__name__)


def _extract_page_text(page: object) -> str:
    """Return stripped text from a pypdf page, tolerating parse errors."""
    extract_text = getattr(page, "extract_text", None)
    if extract_text is None:
        return ""
    try:
        return (extract_text() or "").strip()
    except Exception:
        logger.exception("pypdf failed to extract text from a page; treating it as blank.")
        return ""


def process_pdf_bytes(file_bytes: bytes, source: str = "uploaded.pdf") -> list[Document]:
    """Parse a PDF with pypdf and split the extracted text into chunks.

    Args:
        file_bytes: Raw PDF file content.
        source: Original filename, stored in each chunk's metadata.

    Returns:
        A list of LangChain ``Document`` chunks ready for embedding. Returns an
        empty list when the PDF has no extractable text (e.g. a scanned PDF with
        ``OCR_ENABLED=false``).

    Raises:
        pypdf.errors.PdfReadError: If ``file_bytes`` is not a readable PDF.
    """
    settings = get_settings()

    reader = PdfReader(io.BytesIO(file_bytes))
    page_texts: list[str] = []
    for index, page in enumerate(reader.pages):
        text = _extract_page_text(page)
        if not text and settings.ocr_enabled:
            text = extract_text_from_pdf_page(
                file_bytes,
                page_index=index,
                dpi=settings.ocr_dpi,
                language=settings.ocr_language,
            )
        page_texts.append(text)

    text = "\n\n".join(page_text for page_text in page_texts if page_text)
    if not text.strip():
        logger.warning(
            "No text extracted from %s (is it scanned? Enable OCR_ENABLED=true).", source
        )
        return []

    doc = Document(page_content=text, metadata={"source": source})
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )
    return splitter.split_documents([doc])
