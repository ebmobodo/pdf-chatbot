"""Tests for src.ocr.extract_text_from_pdf_page."""

from unittest.mock import MagicMock, patch


class TestExtractTextFromPdfPage:
    def test_returns_stripped_ocr_text(self):
        from src.ocr import extract_text_from_pdf_page

        with patch("src.ocr.convert_from_bytes") as MockConvert, \
                patch("src.ocr.pytesseract") as MockTess:
            MockConvert.return_value = [MagicMock()]
            MockTess.image_to_string.return_value = "  OCR text  "

            result = extract_text_from_pdf_page(b"pdf bytes", page_index=2)

        assert result == "OCR text"
        MockConvert.assert_called_once_with(
            b"pdf bytes", first_page=3, last_page=3, dpi=300
        )

    def test_uses_configured_dpi_and_language(self):
        from src.ocr import extract_text_from_pdf_page

        with patch("src.ocr.convert_from_bytes") as MockConvert, \
                patch("src.ocr.pytesseract") as MockTess:
            MockConvert.return_value = [MagicMock()]
            MockTess.image_to_string.return_value = "text"

            extract_text_from_pdf_page(b"pdf", page_index=0, dpi=150, language="fra")

        MockConvert.assert_called_once_with(b"pdf", first_page=1, last_page=1, dpi=150)
        MockTess.image_to_string.assert_called_once_with(
            MockConvert.return_value[0], lang="fra"
        )

    def test_returns_empty_when_render_fails(self):
        from src.ocr import extract_text_from_pdf_page

        with patch("src.ocr.convert_from_bytes", side_effect=RuntimeError("poppler missing")), \
                patch("src.ocr.pytesseract") as MockTess:
            assert extract_text_from_pdf_page(b"pdf", page_index=0) == ""
        MockTess.image_to_string.assert_not_called()

    def test_returns_empty_when_no_images(self):
        from src.ocr import extract_text_from_pdf_page

        with patch("src.ocr.convert_from_bytes", return_value=[]), \
                patch("src.ocr.pytesseract") as MockTess:
            assert extract_text_from_pdf_page(b"pdf", page_index=0) == ""
        MockTess.image_to_string.assert_not_called()
