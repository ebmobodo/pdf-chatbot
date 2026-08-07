"""Tests for src.llm_chain.ask_question and _build_llm."""

from unittest.mock import MagicMock, patch

from pydantic import SecretStr
from src.config import Settings


class TestAskQuestion:
    """Tests for the RAG question-answering chain."""

    def test_returns_answer_string(self):
        from src.llm_chain import ask_question

        with (
            patch("src.llm_chain._build_llm"),
            patch("src.llm_chain.create_stuff_documents_chain") as MockStuff,
            patch("src.llm_chain.create_retrieval_chain") as MockRetrieval,
        ):
            mock_combine = MagicMock()
            MockStuff.return_value = mock_combine

            mock_chain = MagicMock()
            mock_chain.invoke.return_value = {"answer": "This is the answer."}
            MockRetrieval.return_value = mock_chain

            result = ask_question("What is RAG?", MagicMock())

        assert result == "This is the answer."

    def test_passes_query_to_chain(self):
        from src.llm_chain import ask_question

        with (
            patch("src.llm_chain._build_llm"),
            patch("src.llm_chain.create_stuff_documents_chain") as MockStuff,
            patch("src.llm_chain.create_retrieval_chain") as MockRetrieval,
        ):
            mock_combine = MagicMock()
            MockStuff.return_value = mock_combine

            mock_chain = MagicMock()
            mock_chain.invoke.return_value = {"answer": "Answer"}
            MockRetrieval.return_value = mock_chain

            ask_question("What is RAG?", MagicMock())

        mock_chain.invoke.assert_called_once_with({"input": "What is RAG?"})

    def test_creates_retrieval_chain(self):
        from src.llm_chain import ask_question

        with (
            patch("src.llm_chain._build_llm"),
            patch("src.llm_chain.create_stuff_documents_chain") as MockStuff,
            patch("src.llm_chain.create_retrieval_chain") as MockRetrieval,
        ):
            mock_combine = MagicMock()
            MockStuff.return_value = mock_combine

            mock_chain = MagicMock()
            mock_chain.invoke.return_value = {"answer": "A"}
            MockRetrieval.return_value = mock_chain

            mock_retriever = MagicMock()
            ask_question("query", mock_retriever)

        MockRetrieval.assert_called_once_with(mock_retriever, mock_combine)

    def test_reraises_and_logs_on_api_failure(self, caplog):
        """ask_question should log the failing providers and re-raise on errors."""
        import logging

        from src.llm_chain import ask_question

        with (
            patch("src.llm_chain._build_llm"),
            patch("src.llm_chain.create_stuff_documents_chain") as MockStuff,
            patch("src.llm_chain.create_retrieval_chain") as MockRetrieval,
        ):
            mock_combine = MagicMock()
            MockStuff.return_value = mock_combine

            mock_chain = MagicMock()
            mock_chain.invoke.side_effect = RuntimeError("API exploded")
            MockRetrieval.return_value = mock_chain

            with caplog.at_level(logging.INFO, logger="src.llm_chain"):
                try:
                    ask_question("boom", MagicMock())
                except RuntimeError as exc:
                    assert str(exc) == "API exploded"
                else:
                    raise AssertionError("expected RuntimeError")

            assert any("gemini-2.5-flash" in rec.message for rec in caplog.records)


class TestBuildLlm:
    """Tests for _build_llm fallback configuration."""

    def _settings(self, **overrides) -> Settings:
        defaults = {
            "supabase_url": "u",
            "supabase_service_key": "k",
            "google_api_key": "g",
            "nvidia_api_key": "n",
            "llm_model": "gemini-2.5-flash",
            "llm_temperature": 0.3,
            "fallback_llm_model": "llama-3.3-70b-versatile",
        }
        defaults.update(overrides)
        return Settings(**defaults)

    def test_uses_correct_llm_settings_without_fallback(self):
        """_build_llm should forward configured model/temperature and no fallback."""
        from src.llm_chain import _build_llm

        settings = self._settings(llm_model="gemini-2.5-flash", llm_temperature=0.1)

        with (
            patch("src.llm_chain.ChatGoogleGenerativeAI") as MockLLM,
            patch("src.llm_chain.ChatGroq") as MockGroq,
        ):
            result = _build_llm(settings)

        MockLLM.assert_called_once_with(model="gemini-2.5-flash", temperature=0.1, max_retries=1)
        MockGroq.assert_not_called()
        assert result is MockLLM.return_value

    def test_builds_fallback_chain_when_groq_key_set(self):
        """_build_llm should chain a ChatGroq fallback when GROQ_API_KEY is set."""
        from src.llm_chain import _build_llm

        settings = self._settings(
            groq_api_key="test-groq-key",
            fallback_llm_model="llama-3.3-70b-versatile",
            llm_temperature=0.5,
        )

        with (
            patch("src.llm_chain.ChatGoogleGenerativeAI") as MockLLM,
            patch("src.llm_chain.ChatGroq") as MockGroq,
        ):
            result = _build_llm(settings)

        MockGroq.assert_called_once_with(
            model="llama-3.3-70b-versatile",
            temperature=0.5,
            api_key=SecretStr("test-groq-key"),
        )
        primary = MockLLM.return_value
        primary.with_fallbacks.assert_called_once_with([MockGroq.return_value])
        assert result is primary.with_fallbacks.return_value

    def test_warns_when_groq_key_missing(self, caplog):
        """_build_llm should warn and skip fallback when GROQ_API_KEY is absent."""
        import logging

        from src.llm_chain import _build_llm

        settings = self._settings()

        with (
            patch("src.llm_chain.ChatGroq") as MockGroq,
            caplog.at_level(logging.WARNING, logger="src.llm_chain"),
        ):
            _build_llm(settings)

        MockGroq.assert_not_called()
        assert any("GROQ_API_KEY" in rec.message for rec in caplog.records)

    def test_groq_requires_groq_package(self):
        """Regression guard: importing langchain_groq must succeed."""
        from langchain_groq import ChatGroq  # noqa: F401

        assert ChatGroq is not None
