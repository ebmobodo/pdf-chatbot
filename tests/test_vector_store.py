"""Tests for src.vector_store."""

from unittest.mock import MagicMock, call, patch

import pytest
from src.vector_store import ensure_https_url, extract_hostname, validate_dns


class TestExtractHostname:
    """Tests for vector_store.extract_hostname."""

    def test_extracts_hostname_from_full_url(self):
        """Should return the hostname portion of a full URL."""
        assert extract_hostname("https://project.supabase.co:5432") == "project.supabase.co"

    def test_extracts_hostname_from_url_with_path(self):
        """Should strip scheme, port, and path from a URL."""
        assert (
            extract_hostname("https://integrate.api.nvidia.com/v1/embeddings")
            == "integrate.api.nvidia.com"
        )

    def test_returns_value_for_bare_string(self):
        """Should return the input unchanged when it has no scheme."""
        assert extract_hostname("test.supabase.co") == "test.supabase.co"

    def test_returns_empty_string(self):
        """Should return an empty string when the input is empty."""
        assert extract_hostname("") == ""


class TestEnsureHttpsUrl:
    """Tests for vector_store.ensure_https_url."""

    def test_returns_https_url_unchanged(self):
        """Should keep the full https:// URL intact."""
        url = "https://project.supabase.co"
        assert ensure_https_url(url, "SUPABASE_URL") == url

    def test_keeps_path_and_other_components(self):
        """Should not strip path/port from an https URL."""
        url = "https://integrate.api.nvidia.com/v1/embeddings"
        assert ensure_https_url(url, "EMBED_BASE_URL") == url

    def test_rejects_scheme_less_url(self):
        """Should raise when the URL is missing the https:// prefix."""
        with pytest.raises(RuntimeError, match="SUPABASE_URL"):
            ensure_https_url("test.supabase.co", "SUPABASE_URL")

    def test_rejects_http_url(self):
        """Should raise for a plain http:// URL."""
        with pytest.raises(RuntimeError, match="https://"):
            ensure_https_url("http://api.nvidia.com/v1", "EMBED_BASE_URL")

    def test_rejects_empty_string(self):
        """Should raise when the URL is empty."""
        with pytest.raises(RuntimeError, match="EMBED_BASE_URL"):
            ensure_https_url("", "EMBED_BASE_URL")


class TestValidateDNS:
    """Tests for vector_store.validate_dns."""

    def test_resolves_known_host_without_error(self):
        """Should call getaddrinfo with the host and port 443."""
        with patch("src.vector_store.socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [(2, 1, 6, "", ("1.2.3.4", 443))]
            validate_dns("api.nvidia.com", service="NVIDIA embeddings")
        mock_gai.assert_called_once_with("api.nvidia.com", 443)

    def test_extracts_hostname_from_full_url_before_resolving(self):
        """Should strip scheme/port from a URL before calling getaddrinfo."""
        with patch("src.vector_store.socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [(2, 1, 6, "", ("1.2.3.4", 443))]
            validate_dns("https://api.nvidia.com:8443/v1", service="NVIDIA embeddings")
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

    def test_error_message_includes_underlying_issue(self):
        """Should surface the real exception text, not a hardcoded message."""
        with (
            patch(
                "src.vector_store.socket.getaddrinfo",
                side_effect=__import__("socket").gaierror(-2, "Name or service not known"),
            ),
            pytest.raises(RuntimeError, match="Name or service not known"),
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

    def test_validates_dns_with_full_urls(self):
        """Should pass full https:// URLs to validate_dns, never pre-stripped hosts."""
        with (
            patch("src.vector_store.SupabaseVectorStore"),
            patch("src.vector_store.NVIDIAEmbeddings"),
            patch("src.vector_store.create_client"),
            patch("src.vector_store.validate_dns") as MockValidate,
        ):
            from src.vector_store import get_vector_store

            get_vector_store()

        MockValidate.assert_has_calls(
            [
                call("https://test.supabase.co", service="Supabase"),
                call(
                    "https://integrate.api.nvidia.com/v1",
                    service="NVIDIA embeddings",
                ),
            ]
        )

    def test_raises_when_supabase_url_is_not_https(self, monkeypatch):
        """Should fail fast when SUPABASE_URL is missing the https:// prefix."""
        monkeypatch.setenv("SUPABASE_URL", "test.supabase.co")
        from src.vector_store import get_vector_store

        with pytest.raises(RuntimeError, match="SUPABASE_URL"):
            get_vector_store()


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
