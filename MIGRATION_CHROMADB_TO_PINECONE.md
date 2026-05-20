# Migration Guide: ChromaDB → Pinecone

## Overview

This document describes the migration from ChromaDB (local vector database) to
Pinecone (managed cloud vector database). The public API of `VectorStore` is
**unchanged** — all existing code that calls `add_documents()`,
`similarity_search()`, `get_retriever()`, etc. continues to work without
modification.

---

## What Changed

| Component | Before (ChromaDB) | After (Pinecone) |
|---|---|---|
| Vector DB | ChromaDB (local, on-disk) | Pinecone Serverless (cloud) |
| LangChain integration | `langchain-chroma` | `langchain-pinecone` |
| Python client | `chromadb` | `pinecone-client` |
| Storage | `data/chroma_db/` directory | Pinecone cloud index |
| Similarity metric | Cosine (default) | Cosine (explicit) |
| Config vars | `CHROMA_PERSIST_DIRECTORY`, `CHROMA_COLLECTION_NAME` | `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, `PINECONE_ENVIRONMENT`, `PINECONE_CLOUD` |

### New features added during migration

- **Automatic index creation** — the index is created on first run if it doesn't exist.
- **Retry handling** — `add_documents` and `similarity_search` use exponential backoff (3 attempts).
- **Connection validation** — `validate_connection()` method to check Pinecone health.
- **Async support** — `asimilarity_search()` and `asimilarity_search_with_score()` for FastAPI.
- **Batch upsert** — large document sets are ingested in configurable batches.
- **Structured logging** — all operations logged via Python `logging` module.
- **Custom exceptions** — `VectorStoreError`, `VectorStoreConnectionError`.

---

## Migration Steps

### 1. Install new dependencies

```bash
pip install -r requirements.txt
```

This replaces `chromadb` and `langchain-chroma` with `pinecone-client`,
`langchain-pinecone`, and `tenacity`.

### 2. Get a Pinecone API key

1. Sign up at [https://app.pinecone.io](https://app.pinecone.io)
2. Create a project (free tier is sufficient for development)
3. Copy your API key from the dashboard

### 3. Update environment variables

Copy `.env.example` to `.env` (or update your existing `.env`):

```bash
# Remove old ChromaDB vars
# CHROMA_PERSIST_DIRECTORY=./data/chroma_db
# CHROMA_COLLECTION_NAME=parking_info

# Add Pinecone vars
PINECONE_API_KEY=your-pinecone-api-key-here
PINECONE_INDEX_NAME=parking-info
PINECONE_ENVIRONMENT=us-east-1
PINECONE_CLOUD=aws
```

### 4. Re-index your data

The old ChromaDB data in `data/chroma_db/` is **not** automatically migrated.
Run the setup command to ingest documents into Pinecone:

```bash
python main.py --setup
```

This will:
1. Load and chunk `parking_info.txt`
2. Create the Pinecone index (if it doesn't exist)
3. Upsert all document embeddings

### 5. Verify

```bash
# Run the test suite
pytest tests/test_vector_store.py -v

# Start the chatbot and ask a question
python main.py
```

### 6. Clean up (optional)

The `data/chroma_db/` directory is no longer used and can be deleted:

```bash
rm -rf data/chroma_db
```

---

## Docker Compatibility

No local storage is needed for the vector database. Remove the `data/chroma_db`
volume mount from your `docker-compose.yml` (if any) and ensure the Pinecone
environment variables are passed to the container:

```yaml
environment:
  - PINECONE_API_KEY=${PINECONE_API_KEY}
  - PINECONE_INDEX_NAME=${PINECONE_INDEX_NAME}
  - PINECONE_ENVIRONMENT=${PINECONE_ENVIRONMENT}
  - PINECONE_CLOUD=${PINECONE_CLOUD}
```

---

## Rollback

To revert to ChromaDB, check out the previous version of these files:
- `src/database/vector_store.py`
- `config/settings.py`
- `requirements.txt`
- `.env`
- `tests/test_vector_store.py`

And run `pip install -r requirements.txt` again.
