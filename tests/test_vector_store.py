"""Tests for src.vector_store."""

from unittest.mock import MagicMock, patch


class TestGetVectorStore:
    """Tests for vector_store.get_vector_store."""

    def test_returns_supabase_vector_store(self):
        """Should return a SupabaseVectorStore instance."""
        with (
            patch("src.vector_store.SupabaseVectorStore") as MockVS,
            patch("src.vector_store.NVIDIAEmbeddings"),
            patch("src.vector_store.create_client"),
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
        ):
            from src.vector_store import get_vector_store

            get_vector_store()

        MockEmb.assert_called_once_with(
            model="nvidia/nv-embedqa-e5-v5",
            base_url="https://integrate.api.nvidia.com/v1",
            nvidia_api_key="test-nvidia-key",
        )

    def test_vector_store_configured_correctly(self):
        """Should pass correct params to SupabaseVectorStore."""
        with (
            patch("src.vector_store.SupabaseVectorStore") as MockVS,
            patch("src.vector_store.NVIDIAEmbeddings") as MockEmb,
            patch("src.vector_store.create_client") as MockCreate,
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
