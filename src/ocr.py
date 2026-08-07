"""OCR helpers for scanned PDF pages.

:mod:`src.document_processor` extracts text with ``pypdf`` and calls
``extract_text_from_pdf_page`` for any page that has no embedded text layer
(common for scanned documents). We render the page to an image with
``pdf2image`` and run Tesseract through ``pytesseract``.

Both Python packages are optional at runtime: if they are missing, or the
``poppler-utils`` system binaries are not installed, this module logs a
warning and returns an empty string so the rest of the application keeps
working. Enable the feature with ``OCR_ENABLED=true``.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

convert_from_bytes: Any = None
pytesseract: Any = None

try:
    import pytesseract as _pytesseract
    from pdf2image import convert_from_bytes as _convert_from_bytes

    pytesseract = _pytesseract
    convert_from_bytes = _convert_from_bytes
except ImportError:  # pragma: no cover - exercised only when optional deps are absent
    pass


def extract_text_from_pdf_page(
    pdf_bytes: bytes,
    page_index: int,
    dpi: int = 300,
    language: str = "eng",
) -> str:
    """Return OCR text for the page at ``page_index`` (0-based)."""
    if convert_from_bytes is None or pytesseract is None:
        logger.warning(
            "OCR requested but pdf2image/pytesseract are not installed; page %d will be skipped.",
            page_index + 1,
        )
        return ""

    try:
        images = convert_from_bytes(
            pdf_bytes,
            first_page=page_index + 1,
            last_page=page_index + 1,
            dpi=dpi,
        )
    except Exception as exc:
        logger.warning(
            "Failed to render page %d for OCR (is poppler-utils installed?): %s",
            page_index + 1,
            exc,
        )
        return ""

    if not images:
        return ""

    return pytesseract.image_to_string(images[0], lang=language).strip()
