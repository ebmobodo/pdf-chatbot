"""RAG chain built on Google Gemini.

Retrieves relevant context through the Supabase-backed retriever, stuffs it
into the prompt, and generates an answer with Gemini. Model name and
temperature are configurable via environment variables (see
:func:`src.config.get_settings`).
"""

from __future__ import annotations

import logging

from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents.stuff import (
    create_stuff_documents_chain,
)
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_google_genai import ChatGoogleGenerativeAI

from src.config import Settings, get_settings

logger = logging.getLogger(__name__)

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


def _build_llm(settings: Settings) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
    )


def ask_question(query: str, retriever: VectorStoreRetriever) -> str:
    """Run the full RAG pipeline: retrieve context, then generate an answer."""
    settings = get_settings()
    llm = _build_llm(settings)
    combine_chain = create_stuff_documents_chain(llm, prompt)
    chain = create_retrieval_chain(retriever, combine_chain)

    logger.debug("Generating answer for query: %s", query)
    result = chain.invoke({"input": query})
    return result["answer"]
