"""OCR helpers for scanned PDF pages.

When a PDF page has no embedded text layer (common for scanned
documents), we render the page to an image with ``pdf2image`` and run
Tesseract through ``pytesseract``.

Both Python packages are optional at runtime: if they are missing, or the
``poppler-utils`` system binaries are not installed, the pipeline logs a
warning and returns an empty string so the rest of the application keeps
working. Enable the feature with ``OCR_ENABLED=true``.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    import pytesseract
    from pdf2image import convert_from_bytes
except ImportError:  # pragma: no cover - exercised only when optional deps are absent
    convert_from_bytes = None
    pytesseract = None


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
