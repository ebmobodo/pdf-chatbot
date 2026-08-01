"""PDF ingestion pipeline powered by Docling.

Uses IBM Docling's ``DocumentConverter`` for enterprise-grade PDF parsing:
layout-aware text extraction, built-in OCR (via RapidOCR), table structure
preservation, and structured markdown output. Replaces the previous pypdf
+ pytesseract stack with a single unified pipeline.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from docling.document_converter import DocumentConverter
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import get_settings

logger = logging.getLogger(__name__)

_converter: DocumentConverter | None = None


def _get_converter() -> DocumentConverter:
    global _converter
    if _converter is None:
        logger.info("Initialising Docling DocumentConverter…")
        _converter = DocumentConverter()
    return _converter


def process_pdf_bytes(file_bytes: bytes, source: str = "uploaded.pdf") -> list[Document]:
    """Parse a PDF with Docling and split the resulting markdown into chunks.

    Args:
        file_bytes: Raw PDF file content.
        source: Original filename, stored in each chunk's metadata.

    Returns:
        A list of LangChain ``Document`` chunks ready for embedding.
    """
    settings = get_settings()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = Path(tmp.name)

    try:
        converter = _get_converter()
        result = converter.convert(str(tmp_path))
        text = result.document.export_to_markdown()
    except Exception:
        logger.exception("Docling failed to parse %s", source)
        raise
    finally:
        tmp_path.unlink(missing_ok=True)

    if not text.strip():
        logger.warning("Docling produced empty output for %s", source)
        return []

    doc = Document(page_content=text, metadata={"source": source})
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )
    return splitter.split_documents([doc])