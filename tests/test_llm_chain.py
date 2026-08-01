"""Tests for src.llm_chain.ask_question."""

from unittest.mock import MagicMock, patch

from src.config import Settings


class TestAskQuestion:
    """Tests for the RAG question-answering chain."""

    def test_returns_answer_string(self):
        from src.llm_chain import ask_question

        with patch("src.llm_chain._build_llm"), \
                patch("src.llm_chain.create_stuff_documents_chain") as MockStuff, \
                patch("src.llm_chain.create_retrieval_chain") as MockRetrieval:
            mock_combine = MagicMock()
            MockStuff.return_value = mock_combine

            mock_chain = MagicMock()
            mock_chain.invoke.return_value = {"answer": "This is the answer."}
            MockRetrieval.return_value = mock_chain

            result = ask_question("What is RAG?", MagicMock())

        assert result == "This is the answer."

    def test_passes_query_to_chain(self):
        from src.llm_chain import ask_question

        with patch("src.llm_chain._build_llm"), \
                patch("src.llm_chain.create_stuff_documents_chain") as MockStuff, \
                patch("src.llm_chain.create_retrieval_chain") as MockRetrieval:
            mock_combine = MagicMock()
            MockStuff.return_value = mock_combine

            mock_chain = MagicMock()
            mock_chain.invoke.return_value = {"answer": "Answer"}
            MockRetrieval.return_value = mock_chain

            ask_question("What is RAG?", MagicMock())

        mock_chain.invoke.assert_called_once_with({"input": "What is RAG?"})

    def test_creates_retrieval_chain(self):
        from src.llm_chain import ask_question

        with patch("src.llm_chain._build_llm"), \
                patch("src.llm_chain.create_stuff_documents_chain") as MockStuff, \
                patch("src.llm_chain.create_retrieval_chain") as MockRetrieval:
            mock_combine = MagicMock()
            MockStuff.return_value = mock_combine

            mock_chain = MagicMock()
            mock_chain.invoke.return_value = {"answer": "A"}
            MockRetrieval.return_value = mock_chain

            mock_retriever = MagicMock()
            ask_question("query", mock_retriever)

        MockRetrieval.assert_called_once_with(mock_retriever, mock_combine)

    def test_uses_correct_llm_settings(self):
        """_build_llm should forward the configured model and temperature."""
        from src.llm_chain import _build_llm

        settings = Settings(
            supabase_url="u",
            supabase_service_key="k",
            google_api_key="g",
            nvidia_api_key="n",
            llm_model="gemini-2.0-flash",
            llm_temperature=0.1,
        )

        with patch("src.llm_chain.ChatGoogleGenerativeAI") as MockLLM:
            _build_llm(settings)

        MockLLM.assert_called_once_with(model="gemini-2.0-flash", temperature=0.1)
