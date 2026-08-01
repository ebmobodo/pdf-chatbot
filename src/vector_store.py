"""Supabase vector store integration.

Connects to the Supabase ``documents`` table (pgvector) through LangChain's
``SupabaseVectorStore`` and embeds chunks with NVIDIA NIM embeddings. All
credentials come from :func:`src.config.get_settings`, so nothing is
hardcoded here.
"""

from __future__ import annotations

import logging

from langchain_community.vectorstores import SupabaseVectorStore
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from supabase.client import ClientOptions, create_client

from src.config import Settings, get_settings

logger = logging.getLogger(__name__)

TABLE_NAME = "documents"
QUERY_NAME = "match_documents"
EMBED_BATCH_SIZE = 10


def _build_embeddings(settings: Settings) -> NVIDIAEmbeddings:
    return NVIDIAEmbeddings(
        model=settings.embed_model,
        base_url=settings.embed_base_url,
        nvidia_api_key=settings.nvidia_api_key,
    )


def get_vector_store() -> SupabaseVectorStore:
    """Build the application vector store backed by Supabase + NVIDIA embeddings."""
    settings = get_settings()

    options = ClientOptions(postgrest_client_timeout=settings.postgrest_timeout)
    supabase = create_client(
        settings.supabase_url,
        settings.supabase_service_key,
        options=options,
    )

    return SupabaseVectorStore(
        client=supabase,
        embedding=_build_embeddings(settings),
        table_name=TABLE_NAME,
        query_name=QUERY_NAME,
        chunk_size=EMBED_BATCH_SIZE,
    )


def save_chunks_to_database(chunks: list) -> None:
    """Embed and persist document chunks into the Supabase ``documents`` table."""
    if not chunks:
        logger.info("No chunks to save; skipping vector store write.")
        return

    logger.info("Embedding %d chunks with NVIDIA and saving to Supabase...", len(chunks))
    vector_store = get_vector_store()
    vector_store.add_documents(chunks)
    logger.info("Saved %d chunks to Supabase.", len(chunks))
