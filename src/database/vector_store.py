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
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

# Heavy imports (torch / sentence-transformers / pinecone) are deferred to
# VectorStore.__init__ so that merely importing this module does NOT trigger
# a 30-60 second torch startup on the first import.

from config.settings import settings

logger = logging.getLogger(__name__)


class VectorStoreError(Exception):
    """Base exception for vector store operations."""


class VectorStoreConnectionError(VectorStoreError):
    """Raised when connection to Pinecone fails."""


class HuggingFaceHubInferenceEmbeddings:
    """Adapter for Hugging Face Hub remote embeddings via InferenceClient."""

    def __init__(self, repo_id: str, token: str):
        from huggingface_hub import InferenceClient  # noqa: PLC0415

        self._client = InferenceClient(token=token)
        self._repo_id = repo_id

    def _extract(self, texts):
        result = self._client.feature_extraction(texts, model=self._repo_id)
        # Convert numpy arrays to pure Python lists (including nested float32 → float)
        import numpy as np
        
        def to_python_list(arr):
            """Recursively convert numpy types to Python native types."""
            if isinstance(arr, np.ndarray):
                return [to_python_list(x) for x in arr]
            elif isinstance(arr, (np.floating, np.integer)):
                return float(arr)
            elif isinstance(arr, (list, tuple)):
                return [to_python_list(x) for x in arr]
            else:
                return arr
        
        return to_python_list(result)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        result = self._extract(texts)
        # Ensure result is a list of lists even if _extract returns a single array
        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], (int, float)):
            return [result]
        return result

    def embed_query(self, text: str) -> List[float]:
        result = self._extract([text])
        # Extract the first embedding from the list
        if isinstance(result, list) and len(result) > 0:
            first = result[0]
            if isinstance(first, list):
                return first
            else:
                return result
        return result


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
        # Lazy-import heavy dependencies so that importing this module doesn't
        # load torch/sentence-transformers/pinecone during server startup.
        from langchain_huggingface import HuggingFaceEmbeddings  # noqa: PLC0415
        from langchain_pinecone import PineconeVectorStore as _PVC  # noqa: PLC0415
        from pinecone import Pinecone, ServerlessSpec  # noqa: PLC0415

        self._PineconeVectorStore = _PVC
        self._ServerlessSpec = ServerlessSpec

        # --- Embedding provider: remote HF Hub ONLY (no local fallback) ---
        provider = getattr(settings, "embedding_provider", "local")
        if provider == "hf_hub":
            token = settings.huggingfacehub_api_token or None
            tried = False

            # First try the LangChain wrapper if installed.
            try:
                from langchain_huggingface_hub import HuggingFaceHubEmbeddings  # type: ignore

                self.embeddings = (
                    HuggingFaceHubEmbeddings(
                        repo_id=settings.embedding_model,
                        huggingfacehub_api_token=token,
                    )
                    if token
                    else HuggingFaceHubEmbeddings(repo_id=settings.embedding_model)
                )
                logger.info("Using remote HuggingFaceHub embeddings (repo=%s)", settings.embedding_model)
                tried = True
            except Exception as exc:
                logger.warning(
                    "langchain_huggingface_hub unavailable or failed; falling back to direct huggingface-hub InferenceClient. (%s)",
                    exc,
                )

            if not tried:
                try:
                    self.embeddings = HuggingFaceHubInferenceEmbeddings(
                        repo_id=settings.embedding_model,
                        token=settings.huggingfacehub_api_token,
                    )
                    logger.info("Using direct Hugging Face Hub Inference embeddings (repo=%s)", settings.embedding_model)
                    tried = True
                except Exception as exc:
                    raise VectorStoreConnectionError(
                        f"Failed to initialize remote Hugging Face Hub embeddings: {exc}"
                    ) from exc

            if not tried:
                raise VectorStoreConnectionError(
                    "Failed to initialize any remote Hugging Face Hub embedding provider."
                )
        else:
            raise VectorStoreConnectionError(
                f"Unsupported embedding provider '{provider}'. To use remote embeddings set EMBEDDING_PROVIDER=hf_hub and provide HUGGINGFACEHUB_API_TOKEN if required."
            )

        # --- Pinecone client ---
        if not settings.pinecone_api_key:
            raise VectorStoreConnectionError("PINECONE_API_KEY is not set. Add it to your .env file.")

        self._pc = Pinecone(api_key=settings.pinecone_api_key)
        self._index_name = settings.pinecone_index_name

        # Ensure the index exists (creates if missing)
        self._ensure_index()

        # --- LangChain wrapper ---
        self.vectorstore = self._PineconeVectorStore(
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
        import concurrent.futures
        def _list():
            return [idx.name for idx in self._pc.list_indexes()]

        # Give Pinecone at most 20 seconds to respond before giving up
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_list)
            try:
                existing = future.result(timeout=20)
            except concurrent.futures.TimeoutError:
                raise VectorStoreConnectionError(
                    "Pinecone list_indexes() timed out after 20s — check network / API key"
                )

        if self._index_name not in existing:
            logger.info("Creating Pinecone index '%s' ...", self._index_name)
            self._pc.create_index(
                name=self._index_name,
                dimension=self.EMBEDDING_DIMENSION,
                metric="cosine",
                spec=self._ServerlessSpec(
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
