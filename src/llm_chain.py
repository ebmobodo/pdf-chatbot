"""RAG chain built on Google Gemini with a Groq fallback.

Retrieves relevant context through the Supabase-backed retriever, stuffs it
into the prompt, and generates an answer with Gemini. If Gemini fails (rate
limits, API key issues, or downtime), the request automatically falls back to
Groq. Model names and temperature are configurable via environment variables
(see :func:`src.config.get_settings`).
"""

from __future__ import annotations

import logging

from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents.stuff import (
    create_stuff_documents_chain,
)
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from pydantic import SecretStr

from src.config import Settings, get_settings

logger = logging.getLogger(__name__)


def _sanitize_for_log(value: str) -> str:
    """Remove line breaks from untrusted text before writing to logs."""
    return value.replace("\r", " ").replace("\n", " ")


_SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions based strictly on the "
    "provided context. If the context does not contain the answer, say so."
    "\n\nContext:\n{context}"
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_PROMPT),
        ("human", "{input}"),
    ]
)


def _build_llm(settings: Settings) -> Runnable:
    """Build the primary Gemini model, chained to a Groq fallback.

    When ``GROQ_API_KEY`` is configured the returned runnable transparently
    retries on Groq whenever the Gemini call fails. Without a Groq key the
    primary model is returned alone (with a logged warning).
    """
    primary_llm = ChatGoogleGenerativeAI(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_retries=1,
    )

    if not settings.groq_api_key:
        logger.warning(
            "GROQ_API_KEY not set; running with Gemini only (no fallback). Model: %s",
            settings.llm_model,
        )
        return primary_llm

    fallback_llm = ChatGroq(
        model=settings.fallback_llm_model,
        temperature=settings.llm_temperature,
        api_key=SecretStr(settings.groq_api_key),
    )
    logger.info(
        "LLM configured: Primary=Gemini(%s) -> Fallback=Groq(%s)",
        settings.llm_model,
        settings.fallback_llm_model,
    )
    return primary_llm.with_fallbacks([fallback_llm])


def ask_question(query: str, retriever: VectorStoreRetriever) -> str:
    """Run the full RAG pipeline: retrieve context, then generate an answer."""
    settings = get_settings()
    llm = _build_llm(settings)
    combine_chain = create_stuff_documents_chain(llm, prompt)
    chain = create_retrieval_chain(retriever, combine_chain)
    sanitized_query = _sanitize_for_log(query)

    logger.debug("Generating answer for query: %s", sanitized_query)
    logger.info(
        "Dispatching API call to primary model: %s (fallback: %s)",
        settings.llm_model,
        settings.fallback_llm_model if settings.groq_api_key else "none",
    )
    try:
        result = chain.invoke({"input": query})
    except Exception:
        logger.exception(
            "All LLM providers failed for query %r (primary=%s, fallback=%s)",
            sanitized_query,
            settings.llm_model,
            settings.fallback_llm_model if settings.groq_api_key else "none",
        )
        raise
    logger.info(
        "LLM call to model %s completed (fallback: %s)",
        settings.llm_model,
        settings.fallback_llm_model if settings.groq_api_key else "none",
    )
    return result["answer"]
