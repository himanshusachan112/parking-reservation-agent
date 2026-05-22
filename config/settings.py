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

    # === Groq (public LLM API — free tier, works on Render/cloud) ===
    # Get your free key at https://console.groq.com
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # === Google Gemini (free tier, works on Render/cloud) ===
    # Get your free key at https://aistudio.google.com/apikey
    # When GOOGLE_API_KEY is set, Gemini is used (takes priority over Groq).
    google_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

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
    # Used as fallback when database_url is not set.
    sql_database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'parking_dynamic.db'}"

    # === PostgreSQL (Primary Production Database) ===
    # Set DATABASE_URL in .env to switch from SQLite to PostgreSQL.
    # Example: postgresql://postgres:password@localhost:5432/parksmart
    # When set, ALL transactional data (bookings, availability, prices) goes here.
    # Leave empty to use SQLite (local dev without PostgreSQL).
    database_url: str = ""

    # CORS allowed origins (comma-separated, no spaces)
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,https://parking-chatbot-mbt9c1lwt-sachansanyam203-gmailcoms-projects.vercel.app"

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

    # === Payment / Frontend URL ===
    # Base URL of the frontend used to build payment links in emails.
    # Override in .env: APP_BASE_URL=https://yoursite.com
    app_base_url: str = "http://localhost:3000"

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Singleton settings instance - import this in other modules
settings = Settings()
