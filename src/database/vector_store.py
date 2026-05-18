"""
Vector Store Module - ChromaDB Integration for RAG.

This module handles:
- Creating and managing the ChromaDB vector database
- Adding documents (text chunks) to the store
- Performing similarity search to find relevant context

HOW VECTOR SEARCH WORKS:
1. Each text chunk is converted to a vector (list of numbers) using OpenAI embeddings
2. Vectors capture the "meaning" of text - similar texts have similar vectors
3. When a user asks a question, we convert it to a vector too
4. We find the closest vectors in the database (cosine similarity)
5. Return the corresponding text chunks as context for the LLM

WHY ChromaDB?
- Free and open-source (no API keys needed for the DB itself)
- Runs locally (no network latency)
- Persistent storage (survives restarts)
- Easy to set up and use
- Can be swapped for Milvus/Pinecone in production
"""

import os
from typing import List, Optional

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

from config.settings import settings


class VectorStore:
    """
    Wrapper around ChromaDB for storing and retrieving parking information.
    
    This class provides a clean interface for:
    - Initializing the vector database
    - Adding documents to the store
    - Searching for relevant documents given a query
    """

    def __init__(self):
        """
        Initialize the VectorStore with OpenAI embeddings and ChromaDB.
        
        The embeddings model (text-embedding-3-small) converts text to 1536-dim vectors.
        ChromaDB stores these vectors persistently on disk.
        """
        # Create the embeddings function using a local HuggingFace model
        # all-MiniLM-L6-v2: free, fast, runs locally, 384-dim vectors
        # No API key needed - the model runs entirely on your machine
        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        # Ensure the storage directory exists
        os.makedirs(settings.chroma_persist_directory, exist_ok=True)

        # Initialize ChromaDB with persistent storage
        self.vectorstore = Chroma(
            collection_name=settings.chroma_collection_name,
            embedding_function=self.embeddings,
            persist_directory=settings.chroma_persist_directory,
        )

    def add_documents(self, documents: List[Document]) -> None:
        """
        Add a list of documents to the vector store.
        
        Each document's text is:
        1. Converted to a vector using the embedding model
        2. Stored in ChromaDB along with the original text and metadata
        
        Args:
            documents: List of LangChain Document objects (text + metadata)
        """
        if not documents:
            raise ValueError("No documents provided to add to the vector store.")

        self.vectorstore.add_documents(documents)
        print(f"✓ Added {len(documents)} documents to the vector store.")

    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        """
        Search for documents most similar to the query.
        
        This is the core of RAG retrieval:
        1. Query text → vector
        2. Find k closest vectors in the database
        3. Return corresponding documents
        
        Args:
            query: The user's question or search text
            k: Number of results to return (default: 4)
            
        Returns:
            List of the k most relevant Document objects
        """
        results = self.vectorstore.similarity_search(query, k=k)
        return results

    def similarity_search_with_score(self, query: str, k: int = 4) -> List[tuple]:
        """
        Search with relevance scores (useful for evaluation).
        
        Returns documents along with their similarity scores.
        Lower score = more similar (it's actually a distance metric).
        
        Args:
            query: The user's question
            k: Number of results to return
            
        Returns:
            List of (Document, score) tuples sorted by relevance
        """
        results = self.vectorstore.similarity_search_with_score(query, k=k)
        return results

    def get_retriever(self, search_kwargs: Optional[dict] = None):
        """
        Get a LangChain Retriever interface for use in chains.
        
        A Retriever is a standard LangChain interface that the RAG chain
        can use to automatically fetch context for each query.
        
        Args:
            search_kwargs: Optional dict with search parameters (e.g., {"k": 5})
            
        Returns:
            A LangChain Retriever object
        """
        if search_kwargs is None:
            search_kwargs = {"k": 4}

        return self.vectorstore.as_retriever(search_kwargs=search_kwargs)

    def get_collection_count(self) -> int:
        """
        Get the number of documents currently in the vector store.
        Useful for checking if the store has been populated.
        """
        return self.vectorstore._collection.count()

    def clear(self) -> None:
        """
        Delete all documents from the vector store.
        Useful for testing or re-indexing.
        """
        # Get all IDs and delete them
        collection = self.vectorstore._collection
        all_ids = collection.get()["ids"]
        if all_ids:
            collection.delete(ids=all_ids)
            print(f"✓ Cleared {len(all_ids)} documents from the vector store.")
