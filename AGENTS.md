# Project Guidelines

## Overview

ParkSmart is a LangGraph-orchestrated parking reservation chatbot with RAG, human-in-the-loop admin approval, MCP tool server, email notifications, and a Next.js frontend. See [README.md](README.md) for the full architecture diagram.

## Build and Test

```bash
# Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_lg

# Initialize databases (first time or after schema changes)
python main.py --setup

# Run the chatbot (terminal mode)
python main.py

# Run evaluation
python main.py --evaluate

# Run tests (161 tests)
python -m pytest

# Start REST API (port 8000)
python -m uvicorn src.api.server:app --reload --port 8000

# Start MCP server (port 8001)
uvicorn src.mcp.mcp_server:mcp_app --port 8001

# Start frontend (port 3000) — requires backend on 8000
cd frontend && npm run dev
```

## Architecture

**LangGraph pipeline** (`src/graph/`): 6-node state graph orchestrating the full reservation lifecycle.  
Flow: `user_interaction → save_reservation → admin_review → notification → mcp_recording → completion`

| Layer | Module | Purpose |
|-------|--------|---------|
| Orchestration | `src/graph/pipeline.py`, `state.py`, `nodes.py` | LangGraph state machine with conditional edges |
| Chat engine | `src/chatbot/chatbot.py` | Conversation state machine (IDLE → COLLECTING → CONFIRMING) |
| RAG | `src/chatbot/rag_chain.py` | Vector retrieval + LLM generation |
| Safety | `src/chatbot/guardrails.py` | Input injection detection + output PII redaction (Presidio) |
| Data | `src/database/sql_store.py` | SQLite via SQLAlchemy — hours, prices, availability, reservations |
| Data | `src/database/vector_store.py` | Pinecone — static parking knowledge for RAG |
| API | `src/api/server.py` | FastAPI REST endpoints for reservations, admin actions, and chat |
| Admin | `src/agents/admin_agent.py` | LangChain agent with tools for reservation review |
| Notify | `src/notifications/email_service.py` | SMTP SSL/STARTTLS with retry, async support, and console fallback |
| MCP | `src/mcp/mcp_server.py`, `mcp_client.py` | Tool server for writing approved reservations to file |
| Masking | `src/utils/masking.py` | Email masking utility (`sa****@gmail.com`) |
| Frontend | `frontend/` | Next.js 16 + shadcn/ui + Zustand — see [frontend/AGENTS.md](frontend/AGENTS.md) |

**Dual database split**: SQL for structured/transactional data (reservations, prices, availability); Pinecone for semantic search over static parking info.

## Configuration

All settings in `config/settings.py` via pydantic `BaseSettings` (reads `.env` automatically). See [.env.example](.env.example) for required variables:
- `DIAL_API_KEY` — LLM access (Azure OpenAI proxy)
- `PINECONE_API_KEY` — Vector DB
- `SMTP_*` / `ADMIN_EMAIL` — Email notifications

**Important**: Always use `from config.settings import settings` to read config — never raw `os.getenv()`. The pydantic BaseSettings reads `.env` automatically; `os.getenv()` only works if `load_dotenv()` was called (which `main.py` does but `uvicorn` does not).

## Conventions

- **State**: `GraphState` TypedDict in `src/graph/state.py` is the single source of truth passed through all pipeline nodes. Each node returns only the fields it changes.
- **Error handling**: Custom exceptions (`VectorStoreError`, `EmailServiceError`). Use `tenacity` retry with exponential backoff for external services (Pinecone, SMTP).
- **PII safety**: All user-facing email display must use `mask_email()` from `src/utils/masking.py`. Guardrails `safe_patterns` list includes masked email regex so Presidio won't re-redact them.
- **DB migrations**: `SQLStore._migrate_schema()` adds missing columns via `ALTER TABLE` on startup. When adding new columns to SQLAlchemy models, also add migration logic there.
- **Singletons**: Graph nodes share the same chatbot/SQL store/email service instances (created in `pipeline.py`). SQLite uses `StaticPool` for in-memory DBs to support multi-threaded access.
- **Chat API state**: `_pipeline_state` in `server.py` is global/mutable — not thread-safe for concurrent requests. Single-session demo only.

## Testing

- One test file per module in `tests/` (e.g., `test_chatbot.py`, `test_sql_store.py`)
- Tests grouped in classes with `setup_method()` for per-test mock initialization
- All external services (LLM, Pinecone, SMTP) are mocked with `unittest.mock.patch()`
- **Mock `settings` object, not `os.environ`**: Use `@patch("src.module.settings", mock_settings)` with a `MagicMock` that has attribute overrides
- Async tests use `@pytest.mark.asyncio`
- In-memory SQLite (`sqlite:///:memory:`) for database tests — no cleanup needed
