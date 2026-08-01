"""Tests for src.document_processor.process_pdf_bytes (Docling-based)."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document


class TestProcessPdfBytes:
    def _make_text(self, text="Some sample text from the document."):
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = text
        mock_converter = MagicMock()
        mock_converter.convert.return_value = mock_result
        mock_tmp = MagicMock()
        mock_tmp.name = "C:\\tmp\\test.pdf"
        return mock_converter, mock_tmp

    # ------------------------------------------------------------------

    def test_returns_list_of_documents(self):
        from src.document_processor import process_pdf_bytes

        converter, mock_tmp = self._make_text()
        with patch("src.document_processor._get_converter", return_value=converter), \
                patch("src.document_processor.tempfile.NamedTemporaryFile") as MockTmp, \
                patch("src.document_processor.Path.unlink"):
            MockTmp.return_value.__enter__.return_value = mock_tmp
            docs = process_pdf_bytes(b"fake pdf", source="test.pdf")

        assert len(docs) == 1
        assert isinstance(docs[0], Document)
        assert "Some sample text from the document." in docs[0].page_content

    def test_metadata_tracks_source(self):
        from src.document_processor import process_pdf_bytes

        converter, mock_tmp = self._make_text("Text.")
        with patch("src.document_processor._get_converter", return_value=converter), \
                patch("src.document_processor.tempfile.NamedTemporaryFile") as MockTmp, \
                patch("src.document_processor.Path.unlink"):
            MockTmp.return_value.__enter__.return_value = mock_tmp
            docs = process_pdf_bytes(b"fake", source="report.pdf")

        assert docs[0].metadata == {"source": "report.pdf"}

    def test_splitter_parameters(self):
        from src.document_processor import process_pdf_bytes

        converter, mock_tmp = self._make_text("Text.")
        mock_splitter = MagicMock()
        mock_splitter.split_documents.return_value = [
            Document(page_content="Chunk 1", metadata={}),
        ]

        with patch("src.document_processor._get_converter", return_value=converter), \
                patch("src.document_processor.RecursiveCharacterTextSplitter") as MockSplitter, \
                patch("src.document_processor.tempfile.NamedTemporaryFile") as MockTmp, \
                patch("src.document_processor.Path.unlink"):
            MockTmp.return_value.__enter__.return_value = mock_tmp
            MockSplitter.return_value = mock_splitter
            docs = process_pdf_bytes(b"fake")

        MockSplitter.assert_called_once_with(
            chunk_size=1000, chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""],
        )
        assert docs == [Document(page_content="Chunk 1", metadata={})]

    def test_temp_file_cleaned_up(self):
        from src.document_processor import process_pdf_bytes

        converter, mock_tmp = self._make_text("Text")
        with patch("src.document_processor._get_converter", return_value=converter), \
                patch("src.document_processor.tempfile.NamedTemporaryFile") as MockTmp, \
                patch("src.document_processor.Path.unlink") as MockUnlink:
            MockTmp.return_value.__enter__.return_value = mock_tmp
            process_pdf_bytes(b"data")

        MockTmp.return_value.__enter__.return_value.write.assert_called_once_with(b"data")
        MockUnlink.assert_called_once_with(missing_ok=True)

    def test_invalid_pdf_raises(self):
        from src.document_processor import process_pdf_bytes

        converter, mock_tmp = self._make_text()
        converter.convert.side_effect = RuntimeError("parse error")

        with patch("src.document_processor._get_converter", return_value=converter), \
                patch("src.document_processor.tempfile.NamedTemporaryFile") as MockTmp, \
                patch("src.document_processor.Path.unlink"):
            MockTmp.return_value.__enter__.return_value = mock_tmp
            with pytest.raises(Exception):
                process_pdf_bytes(b"bad")

    def test_empty_output_returns_empty_list(self):
        from src.document_processor import process_pdf_bytes

        converter, mock_tmp = self._make_text("   ")
        with patch("src.document_processor._get_converter", return_value=converter), \
                patch("src.document_processor.tempfile.NamedTemporaryFile") as MockTmp, \
                patch("src.document_processor.Path.unlink"):
            MockTmp.return_value.__enter__.return_value = mock_tmp
            docs = process_pdf_bytes(b"empty pdf")

        assert docs == []