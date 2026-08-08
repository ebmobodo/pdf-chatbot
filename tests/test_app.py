"""Tests for the Streamlit entry point (app.py).

``app.py`` executes Streamlit calls at module level, so we load it through a
stubbed ``streamlit`` module and re-execute it to simulate a script rerun
when the "Process PDF" button is clicked.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import MagicMock, patch


@contextmanager
def _patch_streamlit(st: MagicMock) -> Iterator[None]:
    """Swap only the ``streamlit`` module in ``sys.modules``.

    Unlike ``patch.dict(sys.modules, ...)`` this leaves every other entry
    untouched, so modules imported while ``app.py`` executes (e.g.
    ``src.vector_store``) are not removed when the patch is torn down.
    """
    original = sys.modules.get("streamlit")
    sys.modules["streamlit"] = st
    try:
        yield
    finally:
        if original is None:
            sys.modules.pop("streamlit", None)
        else:
            sys.modules["streamlit"] = original


class _SessionState(dict):
    """dict that also supports attribute-style access like ``st.session_state``."""

    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


def _make_stub_streamlit() -> MagicMock:
    """Return a MagicMock streamlit stub that supports context managers."""
    st = MagicMock()
    st.session_state = _SessionState()
    st.chat_input.return_value = None
    st.file_uploader.return_value = None
    st.button.return_value = False
    st.cache_resource.side_effect = lambda *args, **kwargs: lambda fn: fn

    st.sidebar.__enter__.return_value = st.sidebar
    st.sidebar.__exit__.return_value = False

    spinner = MagicMock()
    st.spinner.return_value = spinner
    spinner.__enter__.return_value = spinner
    spinner.__exit__.return_value = False

    message = MagicMock()
    st.chat_message.return_value = message
    message.__enter__.return_value = message
    message.__exit__.return_value = False
    return st


def _load_app() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("app_under_test", "app.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pdf_processing_error_surfaces_helpful_message() -> None:
    """Should render an error naming the failing service hosts when saving fails."""
    st = _make_stub_streamlit()
    uploaded = MagicMock()
    uploaded.name = "doc.pdf"
    uploaded.read.return_value = b"%PDF-1.4 fake"
    st.file_uploader.return_value = uploaded
    st.button.return_value = True

    with (
        _patch_streamlit(st),
        patch("src.document_processor.process_pdf_bytes") as mock_process,
        patch("src.vector_store.save_chunks_to_database") as mock_save,
    ):
        mock_process.return_value = [MagicMock()]
        mock_save.side_effect = RuntimeError("boom")
        _load_app()

    assert mock_save.called
    error_calls = [c[0][0] for c in st.error.call_args_list]
    assert any("test.supabase.co" in message for message in error_calls)
    assert any("integrate.api.nvidia.com" in message for message in error_calls)


def test_successful_pdf_processing_notifies_and_marks_processed() -> None:
    """Should show a success message and set pdf_processed on success."""
    st = _make_stub_streamlit()
    uploaded = MagicMock()
    uploaded.name = "doc.pdf"
    uploaded.read.return_value = b"%PDF-1.4 fake"
    st.file_uploader.return_value = uploaded
    st.button.return_value = True

    with (
        _patch_streamlit(st),
        patch("src.document_processor.process_pdf_bytes") as mock_process,
        patch("src.vector_store.save_chunks_to_database"),
    ):
        chunks = [MagicMock()] * 3
        mock_process.return_value = chunks
        _load_app()

    st.success.assert_called_once()
    assert st.session_state["pdf_processed"] == "doc.pdf"
