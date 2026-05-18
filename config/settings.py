"""
Configuration settings for the Parking Space Reservation Chatbot.

This module loads environment variables and provides a centralized
configuration object that all other modules can import.

HOW IT WORKS:
- Uses pydantic-settings to validate and type-check all config values
- Reads from .env file automatically
- Provides sensible defaults so the app runs even without all vars set
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


# Project root directory (2 levels up from config/)
PROJECT_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # === EPAM DIAL (Azure OpenAI Proxy) Configuration ===
    # EPAM DIAL acts as a proxy to Azure OpenAI services
    azure_endpoint: str = "https://ai-proxy.lab.epam.com"

    # Your DIAL API key (provided by EPAM)
    dial_api_key: str = ""

    # Azure OpenAI API version
    api_version: str = "2024-02-01"

    # Which LLM model to use for chat responses
    # gpt-4o for best quality; gpt-4.1-mini-2025-04-14 for cheaper
    llm_model: str = "gpt-4o"

    # Which embedding model to use for vectorizing text
    # all-MiniLM-L6-v2: free local model, no API needed, 384-dim vectors
    embedding_model: str = "all-MiniLM-L6-v2"

    # === ChromaDB (Vector Database) Configuration ===
    # Where to store the vector database files on disk
    chroma_persist_directory: str = str(PROJECT_ROOT / "data" / "chroma_db")

    # Name of the collection inside ChromaDB
    chroma_collection_name: str = "parking_info"

    # === SQL Database Configuration ===
    # SQLite connection string for dynamic data (prices, availability, hours)
    sql_database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'parking_dynamic.db'}"

    # === Guardrails Configuration ===
    # Whether to enable PII/sensitive data filtering
    guardrails_enabled: bool = True

    # Minimum confidence score to flag text as PII (0.0 to 1.0)
    pii_confidence_threshold: float = 0.7

    # === RAG Evaluation Settings ===
    # Number of top documents to retrieve for evaluation
    eval_top_k: int = 5

    # === LLM Parameters ===
    # Temperature controls randomness (0 = deterministic, 1 = creative)
    llm_temperature: float = 0.3

    # Maximum tokens in the response
    llm_max_tokens: int = 1024

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Singleton settings instance - import this in other modules
settings = Settings()
