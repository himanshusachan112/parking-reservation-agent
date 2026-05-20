"""
Tests for the Vector Store module (Pinecone backend).

These tests verify that:
1. Documents can be added to the vector store
2. Similarity search returns relevant results
3. The store handles edge cases properly
4. Connection validation works
5. Index creation and retry logic behave correctly

NOTE: All Pinecone and embedding calls are mocked to avoid
network access and API charges during testing.
"""

from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from langchain_core.documents import Document


class TestVectorStore:
    """Tests for the VectorStore class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.mock_documents = [
            Document(
                page_content="ParkSmart parking is located at 123 Main Street downtown.",
                metadata={"chunk_id": 0, "source": "test"},
            ),
            Document(
                page_content="Standard parking costs $3 per hour and $15 per day.",
                metadata={"chunk_id": 1, "source": "test"},
            ),
            Document(
                page_content="Electric vehicle charging is available on Floor 2 with Tesla Supercharger.",
                metadata={"chunk_id": 2, "source": "test"},
            ),
            Document(
                page_content="The parking has 500 spaces across 5 floors.",
                metadata={"chunk_id": 3, "source": "test"},
            ),
        ]

    def _build_pinecone_mocks(self):
        """Return a dict of common mock objects used across tests."""
        mock_index = MagicMock()
        mock_index.describe_index_stats.return_value = {"total_vector_count": 0}

        mock_pc_instance = MagicMock()
        mock_pc_instance.list_indexes.return_value = [MagicMock(name="parking-info")]
        mock_pc_instance.Index.return_value = mock_index
        mock_pc_instance.describe_index.return_value = MagicMock(status={"ready": True})
        return mock_pc_instance, mock_index

    @patch("src.database.vector_store.settings")
    @patch("src.database.vector_store.PineconeVectorStore")
    @patch("src.database.vector_store.Pinecone")
    @patch("src.database.vector_store.HuggingFaceEmbeddings")
    def test_add_documents(self, mock_embeddings, mock_pinecone_cls, mock_pvs, mock_settings):
        """Test that documents can be added to the vector store."""
        from src.database.vector_store import VectorStore

        mock_settings.pinecone_api_key = "test-key"
        mock_settings.pinecone_index_name = "parking-info"
        mock_settings.pinecone_environment = "us-east-1"
        mock_settings.pinecone_cloud = "aws"
        mock_settings.embedding_model = "all-MiniLM-L6-v2"

        mock_embeddings.return_value = MagicMock()
        mock_pc, mock_idx = self._build_pinecone_mocks()
        mock_pinecone_cls.return_value = mock_pc

        mock_pvs_instance = MagicMock()
        mock_pvs.return_value = mock_pvs_instance

        store = VectorStore()
        store.add_documents(self.mock_documents)

        # Verify documents were added via the LangChain wrapper
        assert mock_pvs_instance.add_documents.called

    @patch("src.database.vector_store.settings")
    @patch("src.database.vector_store.PineconeVectorStore")
    @patch("src.database.vector_store.Pinecone")
    @patch("src.database.vector_store.HuggingFaceEmbeddings")
    def test_similarity_search(self, mock_embeddings, mock_pinecone_cls, mock_pvs, mock_settings):
        """Test that similarity search returns results."""
        from src.database.vector_store import VectorStore

        mock_settings.pinecone_api_key = "test-key"
        mock_settings.pinecone_index_name = "parking-info"
        mock_settings.pinecone_environment = "us-east-1"
        mock_settings.pinecone_cloud = "aws"
        mock_settings.embedding_model = "all-MiniLM-L6-v2"

        mock_embeddings.return_value = MagicMock()
        mock_pc, _ = self._build_pinecone_mocks()
        mock_pinecone_cls.return_value = mock_pc

        expected_results = [self.mock_documents[0]]
        mock_pvs_instance = MagicMock()
        mock_pvs_instance.similarity_search.return_value = expected_results
        mock_pvs.return_value = mock_pvs_instance

        store = VectorStore()
        results = store.similarity_search("Where is the parking located?", k=1)

        assert len(results) == 1
        assert "123 Main Street" in results[0].page_content

    @patch("src.database.vector_store.settings")
    @patch("src.database.vector_store.PineconeVectorStore")
    @patch("src.database.vector_store.Pinecone")
    @patch("src.database.vector_store.HuggingFaceEmbeddings")
    def test_add_empty_documents_raises_error(self, mock_embeddings, mock_pinecone_cls, mock_pvs, mock_settings):
        """Test that adding empty document list raises ValueError."""
        from src.database.vector_store import VectorStore

        mock_settings.pinecone_api_key = "test-key"
        mock_settings.pinecone_index_name = "parking-info"
        mock_settings.pinecone_environment = "us-east-1"
        mock_settings.pinecone_cloud = "aws"
        mock_settings.embedding_model = "all-MiniLM-L6-v2"

        mock_embeddings.return_value = MagicMock()
        mock_pc, _ = self._build_pinecone_mocks()
        mock_pinecone_cls.return_value = mock_pc
        mock_pvs.return_value = MagicMock()

        store = VectorStore()
        with pytest.raises(ValueError, match="No documents provided"):
            store.add_documents([])

    @patch("src.database.vector_store.settings")
    @patch("src.database.vector_store.PineconeVectorStore")
    @patch("src.database.vector_store.Pinecone")
    @patch("src.database.vector_store.HuggingFaceEmbeddings")
    def test_get_retriever(self, mock_embeddings, mock_pinecone_cls, mock_pvs, mock_settings):
        """Test that retriever can be obtained with custom kwargs."""
        from src.database.vector_store import VectorStore

        mock_settings.pinecone_api_key = "test-key"
        mock_settings.pinecone_index_name = "parking-info"
        mock_settings.pinecone_environment = "us-east-1"
        mock_settings.pinecone_cloud = "aws"
        mock_settings.embedding_model = "all-MiniLM-L6-v2"

        mock_embeddings.return_value = MagicMock()
        mock_pc, _ = self._build_pinecone_mocks()
        mock_pinecone_cls.return_value = mock_pc

        mock_pvs_instance = MagicMock()
        mock_pvs.return_value = mock_pvs_instance

        store = VectorStore()
        store.get_retriever(search_kwargs={"k": 3})

        mock_pvs_instance.as_retriever.assert_called_once_with(search_kwargs={"k": 3})

    @patch("src.database.vector_store.settings")
    @patch("src.database.vector_store.PineconeVectorStore")
    @patch("src.database.vector_store.Pinecone")
    @patch("src.database.vector_store.HuggingFaceEmbeddings")
    def test_get_collection_count(self, mock_embeddings, mock_pinecone_cls, mock_pvs, mock_settings):
        """Test that collection count queries Pinecone index stats."""
        from src.database.vector_store import VectorStore

        mock_settings.pinecone_api_key = "test-key"
        mock_settings.pinecone_index_name = "parking-info"
        mock_settings.pinecone_environment = "us-east-1"
        mock_settings.pinecone_cloud = "aws"
        mock_settings.embedding_model = "all-MiniLM-L6-v2"

        mock_embeddings.return_value = MagicMock()
        mock_pc, mock_idx = self._build_pinecone_mocks()
        mock_idx.describe_index_stats.return_value = {"total_vector_count": 42}
        mock_pinecone_cls.return_value = mock_pc
        mock_pvs.return_value = MagicMock()

        store = VectorStore()
        count = store.get_collection_count()

        assert count == 42

    @patch("src.database.vector_store.settings")
    @patch("src.database.vector_store.PineconeVectorStore")
    @patch("src.database.vector_store.Pinecone")
    @patch("src.database.vector_store.HuggingFaceEmbeddings")
    def test_validate_connection_success(self, mock_embeddings, mock_pinecone_cls, mock_pvs, mock_settings):
        """Test connection validation returns True when index is ready."""
        from src.database.vector_store import VectorStore

        mock_settings.pinecone_api_key = "test-key"
        mock_settings.pinecone_index_name = "parking-info"
        mock_settings.pinecone_environment = "us-east-1"
        mock_settings.pinecone_cloud = "aws"
        mock_settings.embedding_model = "all-MiniLM-L6-v2"

        mock_embeddings.return_value = MagicMock()
        mock_pc, _ = self._build_pinecone_mocks()
        mock_pinecone_cls.return_value = mock_pc
        mock_pvs.return_value = MagicMock()

        store = VectorStore()
        assert store.validate_connection() is True

    @patch("src.database.vector_store.settings")
    @patch("src.database.vector_store.PineconeVectorStore")
    @patch("src.database.vector_store.Pinecone")
    @patch("src.database.vector_store.HuggingFaceEmbeddings")
    def test_validate_connection_not_ready(self, mock_embeddings, mock_pinecone_cls, mock_pvs, mock_settings):
        """Test connection validation raises when index is not ready."""
        from src.database.vector_store import VectorStore, VectorStoreConnectionError

        mock_settings.pinecone_api_key = "test-key"
        mock_settings.pinecone_index_name = "parking-info"
        mock_settings.pinecone_environment = "us-east-1"
        mock_settings.pinecone_cloud = "aws"
        mock_settings.embedding_model = "all-MiniLM-L6-v2"

        mock_embeddings.return_value = MagicMock()
        mock_pc, _ = self._build_pinecone_mocks()
        mock_pinecone_cls.return_value = mock_pc
        mock_pvs.return_value = MagicMock()

        store = VectorStore()

        # Now make describe_index return not-ready
        mock_pc.describe_index.return_value = MagicMock(status={"ready": False})

        with pytest.raises(VectorStoreConnectionError):
            store.validate_connection()

    def test_missing_api_key_raises_error(self):
        """Test that missing PINECONE_API_KEY raises VectorStoreConnectionError."""
        from src.database.vector_store import VectorStoreConnectionError

        with (
            patch("src.database.vector_store.settings") as mock_settings,
            patch("src.database.vector_store.HuggingFaceEmbeddings"),
        ):
            mock_settings.pinecone_api_key = ""
            mock_settings.embedding_model = "all-MiniLM-L6-v2"

            from src.database.vector_store import VectorStore

            with pytest.raises(VectorStoreConnectionError, match="PINECONE_API_KEY"):
                VectorStore()

    @patch("src.database.vector_store.settings")
    @patch("src.database.vector_store.PineconeVectorStore")
    @patch("src.database.vector_store.Pinecone")
    @patch("src.database.vector_store.HuggingFaceEmbeddings")
    def test_clear_deletes_and_recreates_index(self, mock_embeddings, mock_pinecone_cls, mock_pvs, mock_settings):
        """Test that clear() deletes the index and recreates it."""
        from src.database.vector_store import VectorStore

        mock_settings.pinecone_api_key = "test-key"
        mock_settings.pinecone_index_name = "parking-info"
        mock_settings.pinecone_environment = "us-east-1"
        mock_settings.pinecone_cloud = "aws"
        mock_settings.embedding_model = "all-MiniLM-L6-v2"

        mock_embeddings.return_value = MagicMock()
        mock_pc, _ = self._build_pinecone_mocks()
        mock_pinecone_cls.return_value = mock_pc
        mock_pvs.return_value = MagicMock()

        store = VectorStore()
        store.clear()

        mock_pc.delete_index.assert_called_once_with("parking-info")

    @patch("src.database.vector_store.settings")
    @patch("src.database.vector_store.PineconeVectorStore")
    @patch("src.database.vector_store.Pinecone")
    @patch("src.database.vector_store.HuggingFaceEmbeddings")
    def test_similarity_search_with_score(self, mock_embeddings, mock_pinecone_cls, mock_pvs, mock_settings):
        """Test that similarity_search_with_score returns (doc, score) tuples."""
        from src.database.vector_store import VectorStore

        mock_settings.pinecone_api_key = "test-key"
        mock_settings.pinecone_index_name = "parking-info"
        mock_settings.pinecone_environment = "us-east-1"
        mock_settings.pinecone_cloud = "aws"
        mock_settings.embedding_model = "all-MiniLM-L6-v2"

        mock_embeddings.return_value = MagicMock()
        mock_pc, _ = self._build_pinecone_mocks()
        mock_pinecone_cls.return_value = mock_pc

        expected = [(self.mock_documents[0], 0.95)]
        mock_pvs_instance = MagicMock()
        mock_pvs_instance.similarity_search_with_score.return_value = expected
        mock_pvs.return_value = mock_pvs_instance

        store = VectorStore()
        results = store.similarity_search_with_score("parking location", k=1)

        assert len(results) == 1
        assert results[0][1] == 0.95
