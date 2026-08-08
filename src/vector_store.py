"""Supabase vector store integration.

Connects to the Supabase ``documents`` table (pgvector) through LangChain's
``SupabaseVectorStore`` and embeds chunks with NVIDIA NIM embeddings. All
credentials come from :func:`src.config.get_settings`, so nothing is
hardcoded here.

Before making any network call the target hosts are resolved up front so a
misconfigured/malformed URL (the classic ``[Errno -2] Name or service not
known`` crash) fails fast with a clear message instead of a bare DNS error.
"""

from __future__ import annotations

import logging
import socket
from urllib.parse import urlparse

from langchain_community.vectorstores import SupabaseVectorStore
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from supabase import ClientOptions, create_client

from src.config import Settings, get_settings

logger = logging.getLogger(__name__)

TABLE_NAME = "documents"
QUERY_NAME = "match_documents"
EMBED_BATCH_SIZE = 10


def host_from_url(url: str) -> str:
    """Return the hostname portion of ``url``, falling back to the raw value."""
    try:
        return urlparse(url).hostname or url
    except ValueError:
        return url


def validate_dns(host: str, *, service: str) -> None:
    """Resolve ``host`` so connection errors fail fast with context.

    Raises:
        RuntimeError: When DNS resolution fails (``socket.gaierror``).
    """
    try:
        socket.getaddrinfo(host, 443)
    except socket.gaierror as exc:
        logger.exception("DNS resolution failed for %s host %r.", service, host)
        raise RuntimeError(
            f"Cannot resolve host '{host}' for {service}. Check that the "
            f"{'SUPABASE_URL' if service == 'Supabase' else 'EMBED_BASE_URL'} "
            "environment variable points to a reachable, publicly resolvable URL."
        ) from exc


def _build_embeddings(settings: Settings) -> NVIDIAEmbeddings:
    return NVIDIAEmbeddings(
        model=settings.embed_model,
        base_url=settings.embed_base_url,
        nvidia_api_key=settings.nvidia_api_key,
    )


def get_vector_store() -> SupabaseVectorStore:
    """Build the application vector store backed by Supabase + NVIDIA embeddings."""
    settings = get_settings()

    supabase_host = host_from_url(settings.supabase_url)
    embed_host = host_from_url(settings.embed_base_url)
    logger.info(
        "Connecting to Supabase at host=%s and NVIDIA embeddings at host=%s.",
        supabase_host,
        embed_host,
    )

    validate_dns(supabase_host, service="Supabase")
    validate_dns(embed_host, service="NVIDIA embeddings")

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
