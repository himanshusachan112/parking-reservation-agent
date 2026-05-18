"""
Tests for the Vector Store module.

These tests verify that:
1. Documents can be added to the vector store
2. Similarity search returns relevant results
3. The store handles edge cases properly

NOTE: These tests use a temporary in-memory ChromaDB instance
to avoid polluting the production database.
"""

import pytest
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document


class TestVectorStore:
    """Tests for the VectorStore class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # We mock the OpenAI embeddings to avoid API calls during testing
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

    @patch("src.database.vector_store.HuggingFaceEmbeddings")
    @patch("src.database.vector_store.Chroma")
    def test_add_documents(self, mock_chroma, mock_embeddings):
        """Test that documents can be added to the vector store."""
        from src.database.vector_store import VectorStore

        # Setup mocks
        mock_embeddings_instance = MagicMock()
        mock_embeddings.return_value = mock_embeddings_instance
        mock_chroma_instance = MagicMock()
        mock_chroma.return_value = mock_chroma_instance

        # Create vector store and add documents
        store = VectorStore()
        store.add_documents(self.mock_documents)

        # Verify documents were added
        mock_chroma_instance.add_documents.assert_called_once_with(self.mock_documents)

    @patch("src.database.vector_store.HuggingFaceEmbeddings")
    @patch("src.database.vector_store.Chroma")
    def test_similarity_search(self, mock_chroma, mock_embeddings):
        """Test that similarity search returns results."""
        from src.database.vector_store import VectorStore

        # Setup mocks
        mock_embeddings_instance = MagicMock()
        mock_embeddings.return_value = mock_embeddings_instance
        mock_chroma_instance = MagicMock()
        mock_chroma.return_value = mock_chroma_instance

        # Configure mock to return relevant documents
        expected_results = [self.mock_documents[0]]
        mock_chroma_instance.similarity_search.return_value = expected_results

        # Perform search
        store = VectorStore()
        results = store.similarity_search("Where is the parking located?", k=1)

        # Verify results
        assert len(results) == 1
        assert "123 Main Street" in results[0].page_content

    @patch("src.database.vector_store.HuggingFaceEmbeddings")
    @patch("src.database.vector_store.Chroma")
    def test_add_empty_documents_raises_error(self, mock_chroma, mock_embeddings):
        """Test that adding empty document list raises ValueError."""
        from src.database.vector_store import VectorStore

        mock_embeddings.return_value = MagicMock()
        mock_chroma.return_value = MagicMock()

        store = VectorStore()
        with pytest.raises(ValueError, match="No documents provided"):
            store.add_documents([])

    @patch("src.database.vector_store.HuggingFaceEmbeddings")
    @patch("src.database.vector_store.Chroma")
    def test_get_retriever(self, mock_chroma, mock_embeddings):
        """Test that retriever can be obtained with custom kwargs."""
        from src.database.vector_store import VectorStore

        mock_embeddings.return_value = MagicMock()
        mock_chroma_instance = MagicMock()
        mock_chroma.return_value = mock_chroma_instance

        store = VectorStore()
        retriever = store.get_retriever(search_kwargs={"k": 3})

        mock_chroma_instance.as_retriever.assert_called_once_with(search_kwargs={"k": 3})
