"""Tests for src.vector_store."""

from unittest.mock import MagicMock, patch

import pytest
from src.vector_store import host_from_url, validate_dns


class TestHostFromUrl:
    """Tests for vector_store.host_from_url."""

    def test_extracts_hostname_from_full_url(self):
        """Should return the hostname portion of a full URL."""
        assert host_from_url("https://project.supabase.co:5432") == "project.supabase.co"

    def test_returns_raw_value_for_bare_string(self):
        """Should fall back to the input when it has no scheme."""
        assert host_from_url("test.supabase.co") == "test.supabase.co"

    def test_returns_raw_value_for_empty_string(self):
        """Should return an empty string when the URL is empty."""
        assert host_from_url("") == ""


class TestValidateDNS:
    """Tests for vector_store.validate_dns."""

    def test_resolves_known_host_without_error(self):
        """Should call getaddrinfo with the host and port 443."""
        with patch("src.vector_store.socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [(2, 1, 6, "", ("1.2.3.4", 443))]
            validate_dns("api.nvidia.com", service="NVIDIA embeddings")
        mock_gai.assert_called_once_with("api.nvidia.com", 443)

    def test_raises_runtime_error_on_dns_failure(self):
        """Should raise a helpful RuntimeError when getaddrinfo raises gaierror."""
        with (
            patch(
                "src.vector_store.socket.getaddrinfo",
                side_effect=__import__("socket").gaierror(-2, "Name or service not known"),
            ),
            pytest.raises(RuntimeError, match="api.nvidia.com"),
        ):
            validate_dns("api.nvidia.com", service="NVIDIA embeddings")


class TestGetVectorStore:
    """Tests for vector_store.get_vector_store."""

    def test_returns_supabase_vector_store(self):
        """Should return a SupabaseVectorStore instance."""
        with (
            patch("src.vector_store.SupabaseVectorStore") as MockVS,
            patch("src.vector_store.NVIDIAEmbeddings"),
            patch("src.vector_store.create_client"),
            patch("src.vector_store.validate_dns"),
        ):
            mock_instance = MagicMock()
            MockVS.return_value = mock_instance

            from src.vector_store import get_vector_store

            result = get_vector_store()

        assert result is mock_instance

    def test_initializes_supabase_with_env_vars(self):
        """Should create the Supabase client with URL and service key."""
        with (
            patch("src.vector_store.SupabaseVectorStore"),
            patch("src.vector_store.NVIDIAEmbeddings"),
            patch("src.vector_store.create_client") as MockCreate,
            patch("src.vector_store.validate_dns"),
        ):
            from src.vector_store import get_vector_store

            get_vector_store()

        args, kwargs = MockCreate.call_args
        assert args[0] == "https://test.supabase.co"
        assert args[1] == "test-service-key"

    def test_initializes_nvidia_embeddings(self):
        """Should create NVIDIA embeddings with model, base URL, and API key."""
        with (
            patch("src.vector_store.SupabaseVectorStore"),
            patch("src.vector_store.NVIDIAEmbeddings") as MockEmb,
            patch("src.vector_store.create_client"),
            patch("src.vector_store.validate_dns"),
        ):
            from src.vector_store import get_vector_store

            get_vector_store()

        MockEmb.assert_called_once_with(
            model="nvidia/nemotron-3-embed-1b",
            base_url="https://integrate.api.nvidia.com/v1",
            nvidia_api_key="test-nvidia-key",
        )

    def test_vector_store_configured_correctly(self):
        """Should pass correct params to SupabaseVectorStore."""
        with (
            patch("src.vector_store.SupabaseVectorStore") as MockVS,
            patch("src.vector_store.NVIDIAEmbeddings") as MockEmb,
            patch("src.vector_store.create_client") as MockCreate,
            patch("src.vector_store.validate_dns"),
        ):
            mock_supabase = MagicMock()
            MockCreate.return_value = mock_supabase

            mock_embeddings = MagicMock()
            MockEmb.return_value = mock_embeddings

            from src.vector_store import get_vector_store

            get_vector_store()

        MockVS.assert_called_once_with(
            client=mock_supabase,
            embedding=mock_embeddings,
            table_name="documents",
            query_name="match_documents",
            chunk_size=10,
        )


class TestSaveChunksToDatabase:
    """Tests for vector_store.save_chunks_to_database."""

    def test_calls_add_documents(self, sample_chunks):
        """Should call add_documents on the vector store with chunks."""
        with patch("src.vector_store.get_vector_store") as MockGetVS:
            mock_vs = MagicMock()
            MockGetVS.return_value = mock_vs

            from src.vector_store import save_chunks_to_database

            save_chunks_to_database(sample_chunks)

        mock_vs.add_documents.assert_called_once_with(sample_chunks)

    def test_skips_add_documents_for_empty_list(self):
        """Should not call add_documents when there are no chunks."""
        with patch("src.vector_store.get_vector_store") as MockGetVS:
            mock_vs = MagicMock()
            MockGetVS.return_value = mock_vs

            from src.vector_store import save_chunks_to_database

            save_chunks_to_database([])

        MockGetVS.assert_not_called()
        mock_vs.add_documents.assert_not_called()
