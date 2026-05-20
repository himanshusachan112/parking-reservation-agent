"""
Vector Store Module - Pinecone Integration for RAG.

This module handles:
- Creating and managing a Pinecone vector index
- Adding documents (text chunks) with embeddings
- Performing similarity search to find relevant context
- Async support for FastAPI integration
- Retry handling and connection validation

HOW VECTOR SEARCH WORKS:
1. Each text chunk is converted to a 384-dim vector using sentence-transformers/all-MiniLM-L6-v2
2. Vectors capture the "meaning" of text - similar texts have similar vectors
3. When a user asks a question, we convert it to a vector too
4. We find the closest vectors in Pinecone (cosine similarity)
5. Return the corresponding text chunks as context for the LLM

WHY Pinecone?
- Fully managed cloud vector database (no infrastructure to maintain)
- Sub-100ms queries at any scale
- Built-in high availability and durability
- Native metadata filtering
- Production-grade with SLA
"""

import logging
import time
import uuid
from typing import List, Optional, Tuple

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config.settings import settings

logger = logging.getLogger(__name__)


class VectorStoreError(Exception):
    """Base exception for vector store operations."""


class VectorStoreConnectionError(VectorStoreError):
    """Raised when connection to Pinecone fails."""


class VectorStore:
    """
    Wrapper around Pinecone for storing and retrieving parking information.

    This class provides a clean interface for:
    - Initializing the Pinecone index and embeddings
    - Adding documents to the store (with batching)
    - Searching for relevant documents given a query
    - Async variants for FastAPI integration
    - Connection validation and retry handling
    """

    # all-MiniLM-L6-v2 produces 384-dimensional vectors
    EMBEDDING_DIMENSION = 384

    def __init__(self):
        """
        Initialize the VectorStore with HuggingFace embeddings and Pinecone.

        Steps:
        1. Create the local embedding model (all-MiniLM-L6-v2, 384-dim)
        2. Connect to Pinecone using API key
        3. Create the index if it does not exist (cosine similarity)
        4. Wrap with LangChain PineconeVectorStore for chain compatibility
        """
        # --- Embedding model (runs locally, no API key needed) ---
        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        # --- Pinecone client ---
        if not settings.pinecone_api_key:
            raise VectorStoreConnectionError("PINECONE_API_KEY is not set. Add it to your .env file.")

        self._pc = Pinecone(api_key=settings.pinecone_api_key)
        self._index_name = settings.pinecone_index_name

        # Ensure the index exists (creates if missing)
        self._ensure_index()

        # --- LangChain wrapper ---
        self.vectorstore = PineconeVectorStore(
            index=self._pc.Index(self._index_name),
            embedding=self.embeddings,
            text_key="text",
        )

        logger.info("VectorStore initialised — index=%s", self._index_name)

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def _ensure_index(self) -> None:
        """Create the Pinecone index if it does not already exist."""
        existing = [idx.name for idx in self._pc.list_indexes()]
        if self._index_name not in existing:
            logger.info("Creating Pinecone index '%s' ...", self._index_name)
            self._pc.create_index(
                name=self._index_name,
                dimension=self.EMBEDDING_DIMENSION,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud=settings.pinecone_cloud,
                    region=settings.pinecone_environment,
                ),
            )
            # Wait until the index is ready
            self._wait_for_index_ready()
            logger.info("Index '%s' created.", self._index_name)
        else:
            logger.debug("Index '%s' already exists.", self._index_name)

    def _wait_for_index_ready(self, timeout: int = 120) -> None:
        """Block until the Pinecone index reports ready status."""
        start = time.time()
        while time.time() - start < timeout:
            desc = self._pc.describe_index(self._index_name)
            if desc.status.get("ready", False):
                return
            time.sleep(2)
        raise VectorStoreConnectionError(f"Index '{self._index_name}' not ready after {timeout}s.")

    def validate_connection(self) -> bool:
        """
        Check that the Pinecone index is reachable and ready.

        Returns:
            True if connection is healthy.

        Raises:
            VectorStoreConnectionError on failure.
        """
        try:
            desc = self._pc.describe_index(self._index_name)
            if not desc.status.get("ready", False):
                raise VectorStoreConnectionError(f"Index '{self._index_name}' exists but is not ready.")
            return True
        except Exception as exc:
            raise VectorStoreConnectionError(f"Failed to validate Pinecone connection: {exc}") from exc

    # ------------------------------------------------------------------
    # Document ingestion
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def add_documents(self, documents: List[Document], batch_size: int = 100) -> None:
        """
        Add documents to Pinecone in batches with automatic retry.

        Args:
            documents: List of LangChain Document objects (text + metadata).
            batch_size: Number of documents per upsert batch.

        Raises:
            ValueError: If the document list is empty.
        """
        if not documents:
            raise ValueError("No documents provided to add to the vector store.")

        # Assign stable IDs so re-ingestion is idempotent
        for doc in documents:
            if "id" not in doc.metadata:
                doc.metadata["id"] = str(uuid.uuid4())

        total = len(documents)
        for i in range(0, total, batch_size):
            batch = documents[i : i + batch_size]
            self.vectorstore.add_documents(batch)
            logger.debug("Upserted batch %d–%d / %d", i, i + len(batch), total)

        logger.info("Added %d documents to Pinecone index '%s'.", total, self._index_name)
        print(f"✓ Added {total} documents to the vector store.")

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        """
        Find the k documents most similar to *query* (cosine similarity).

        Args:
            query: The user's question or search text.
            k: Number of results to return (default: 4).

        Returns:
            List of the k most relevant Document objects.
        """
        results = self.vectorstore.similarity_search(query, k=k)
        return results

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def similarity_search_with_score(self, query: str, k: int = 4) -> List[Tuple[Document, float]]:
        """
        Search with relevance scores (useful for evaluation).

        Returns documents paired with their cosine-similarity score.
        Higher score = more similar (range 0–1 for cosine).

        Args:
            query: The user's question.
            k: Number of results to return.

        Returns:
            List of (Document, score) tuples sorted by relevance (descending).
        """
        results = self.vectorstore.similarity_search_with_score(query, k=k)
        return results

    # ------------------------------------------------------------------
    # Async search (for FastAPI / async chains)
    # ------------------------------------------------------------------

    async def asimilarity_search(self, query: str, k: int = 4) -> List[Document]:
        """Async version of similarity_search for use inside async endpoints."""
        return await self.vectorstore.asimilarity_search(query, k=k)

    async def asimilarity_search_with_score(self, query: str, k: int = 4) -> List[Tuple[Document, float]]:
        """Async version of similarity_search_with_score."""
        return await self.vectorstore.asimilarity_search_with_relevance_scores(query, k=k)

    # ------------------------------------------------------------------
    # Retriever interface
    # ------------------------------------------------------------------

    def get_retriever(self, search_kwargs: Optional[dict] = None):
        """
        Get a LangChain Retriever interface for use in RAG chains.

        Args:
            search_kwargs: Optional dict with search parameters (e.g., {"k": 5}).

        Returns:
            A LangChain Retriever backed by Pinecone.
        """
        if search_kwargs is None:
            search_kwargs = {"k": 4}
        return self.vectorstore.as_retriever(search_kwargs=search_kwargs)

    # ------------------------------------------------------------------
    # Collection info & maintenance
    # ------------------------------------------------------------------

    def get_collection_count(self) -> int:
        """
        Return the total number of vectors in the Pinecone index.

        Note: Pinecone stats may be eventually consistent; a short delay
        after upsert is normal.
        """
        stats = self._pc.Index(self._index_name).describe_index_stats()
        return stats.get("total_vector_count", 0)

    def clear(self) -> None:
        """
        Delete ALL vectors from the Pinecone index.

        This deletes the index and recreates it (Pinecone's recommended
        approach for full wipes on serverless indexes).
        """
        logger.warning("Clearing all vectors from index '%s'.", self._index_name)
        self._pc.delete_index(self._index_name)
        self._ensure_index()
        # Re-create the LangChain wrapper against the fresh index
        self.vectorstore = PineconeVectorStore(
            index=self._pc.Index(self._index_name),
            embedding=self.embeddings,
            text_key="text",
        )
        print("✓ Cleared all documents from the vector store.")
