import os

import pytest
from langchain_core.documents import Document

_TEST_ENV = {
    "GOOGLE_API_KEY": "test-google-key",
    "NVIDIA_API_KEY": "test-nvidia-key",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_KEY": "test-service-key",
}


@pytest.fixture(autouse=True)
def _set_env_vars():
    """Pin required env vars before any test runs so tests never touch real secrets."""
    previous = {key: os.environ.get(key) for key in _TEST_ENV}
    os.environ.update(_TEST_ENV)
    yield
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
def sample_chunks() -> list[Document]:
    return [
        Document(
            page_content="Introduction to RAG systems.",
            metadata={"source": "doc.pdf", "page": 0},
        ),
        Document(
            page_content="Retrieval-Augmented Generation combines retrieval with generation.",
            metadata={"source": "doc.pdf", "page": 1},
        ),
        Document(
            page_content="LangChain provides tools for building RAG pipelines.",
            metadata={"source": "doc.pdf", "page": 1},
        ),
    ]


@pytest.fixture
def fake_pdf_bytes() -> bytes:
    return b"%PDF-1.4 fake pdf content for testing purposes"
