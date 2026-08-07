"""Tests for src.document_processor.process_pdf_bytes (pypdf-based)."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document


class TestProcessPdfBytes:
    @staticmethod
    def _reader(*page_texts: str) -> MagicMock:
        reader = MagicMock()
        pages = []
        for text in page_texts:
            page = MagicMock()
            page.extract_text.return_value = text
            pages.append(page)
        reader.pages = pages
        return reader

    # ------------------------------------------------------------------

    def test_returns_list_of_documents(self):
        from src.document_processor import process_pdf_bytes

        reader = self._reader("Some sample text from the document.")
        with patch("src.document_processor.PdfReader", return_value=reader):
            docs = process_pdf_bytes(b"fake pdf", source="test.pdf")

        assert len(docs) == 1
        assert isinstance(docs[0], Document)
        assert "Some sample text from the document." in docs[0].page_content

    def test_metadata_tracks_source(self):
        from src.document_processor import process_pdf_bytes

        reader = self._reader("Text.")
        with patch("src.document_processor.PdfReader", return_value=reader):
            docs = process_pdf_bytes(b"fake", source="report.pdf")

        assert docs[0].metadata == {"source": "report.pdf"}

    def test_multiple_pages_are_joined(self):
        from src.document_processor import process_pdf_bytes

        reader = self._reader("Page one", "Page two")
        with patch("src.document_processor.PdfReader", return_value=reader):
            docs = process_pdf_bytes(b"two pages")

        assert "Page one\n\nPage two" in docs[0].page_content

    def test_splitter_parameters(self):
        from src.document_processor import process_pdf_bytes

        reader = self._reader("Text.")
        mock_splitter = MagicMock()
        mock_splitter.split_documents.return_value = [
            Document(page_content="Chunk 1", metadata={}),
        ]

        with (
            patch("src.document_processor.PdfReader", return_value=reader),
            patch("src.document_processor.RecursiveCharacterTextSplitter") as MockSplitter,
        ):
            MockSplitter.return_value = mock_splitter
            docs = process_pdf_bytes(b"fake")

        MockSplitter.assert_called_once_with(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""],
        )
        assert docs == [Document(page_content="Chunk 1", metadata={})]

    def test_empty_output_returns_empty_list(self):
        from src.document_processor import process_pdf_bytes

        reader = self._reader("   ")
        with patch("src.document_processor.PdfReader", return_value=reader):
            docs = process_pdf_bytes(b"empty pdf")

        assert docs == []

    def test_blank_page_uses_ocr_when_enabled(self, monkeypatch):
        from src.document_processor import process_pdf_bytes

        monkeypatch.setenv("OCR_ENABLED", "true")
        reader = self._reader("")
        with (
            patch("src.document_processor.PdfReader", return_value=reader),
            patch(
                "src.document_processor.extract_text_from_pdf_page",
                return_value="OCR text",
            ) as mock_ocr,
        ):
            docs = process_pdf_bytes(b"scanned", source="scan.pdf")

        assert "OCR text" in docs[0].page_content
        mock_ocr.assert_called_once_with(b"scanned", page_index=0, dpi=300, language="eng")

    def test_ocr_not_called_when_text_present(self):
        from src.document_processor import process_pdf_bytes

        reader = self._reader("Real text")
        with (
            patch("src.document_processor.PdfReader", return_value=reader),
            patch("src.document_processor.extract_text_from_pdf_page") as mock_ocr,
        ):
            process_pdf_bytes(b"texty")

        mock_ocr.assert_not_called()

    def test_page_extract_error_is_treated_as_blank(self):
        from src.document_processor import process_pdf_bytes

        page = MagicMock()
        page.extract_text.side_effect = RuntimeError("boom")
        reader = MagicMock()
        reader.pages = [page]

        with (
            patch("src.document_processor.PdfReader", return_value=reader),
            patch("src.document_processor.extract_text_from_pdf_page") as mock_ocr,
        ):
            docs = process_pdf_bytes(b"pdf")

        assert docs == []
        mock_ocr.assert_not_called()

    def test_page_without_extract_text_is_blank(self):
        from src.document_processor import process_pdf_bytes

        reader = MagicMock()
        reader.pages = [object()]

        with patch("src.document_processor.PdfReader", return_value=reader):
            docs = process_pdf_bytes(b"pdf")

        assert docs == []

    def test_invalid_pdf_raises(self):
        from src.document_processor import process_pdf_bytes

        with (
            patch(
                "src.document_processor.PdfReader",
                side_effect=RuntimeError("not a pdf"),
            ),
            pytest.raises(RuntimeError, match="not a pdf"),
        ):
            process_pdf_bytes(b"bad")
