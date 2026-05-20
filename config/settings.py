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

from pydantic import ConfigDict
from pydantic_settings import BaseSettings

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

    # === Pinecone (Vector Database) Configuration ===
    # Pinecone API key (get from https://app.pinecone.io)
    pinecone_api_key: str = ""

    # Name of the Pinecone index
    pinecone_index_name: str = "parking"

    # Pinecone serverless environment / region
    pinecone_environment: str = "us-east-1"

    # Pinecone cloud provider (aws, gcp, azure)
    pinecone_cloud: str = "aws"

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

    # === Email / SMTP Configuration ===
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_username: str = ""
    smtp_password: str = ""
    admin_email: str = "admin@parksmart.com"

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Singleton settings instance - import this in other modules
settings = Settings()
