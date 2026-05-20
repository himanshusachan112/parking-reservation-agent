# ParkSmart — Stage 4 Implementation Report

> **Auto-generated** on May 21, 2026 at 03:11
> by `create_stage4_implementation.py`

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Project Structure](#2-project-structure)
3. [Technology Choices](#3-technology-choices)
4. [Backend Modules](#4-backend-modules)
5. [Frontend Modules](#5-frontend-modules)
6. [LangGraph Orchestration](#6-langgraph-orchestration)
7. [RAG Pipeline](#7-rag-pipeline)
8. [Human-in-the-Loop Workflow](#8-human-in-the-loop-workflow)
9. [Request Flow Analysis](#9-request-flow-analysis)
10. [Admin Approval Flow](#10-admin-approval-flow)
11. [Vector Search Flow](#11-vector-search-flow)
12. [Notification Flow](#12-notification-flow)
13. [Docker Setup](#13-docker-setup)
14. [CI/CD Pipeline](#14-cicd-pipeline)
15. [Terraform Infrastructure](#15-terraform-infrastructure)
16. [Testing Summary](#16-testing-summary)
17. [Code Metrics](#17-code-metrics)

---

## 1. Executive Summary

ParkSmart is a **full-stack AI parking reservation platform** built across four
iterative development stages. It combines a LangChain RAG chatbot with LangGraph
orchestration, a FastAPI REST backend, a Next.js frontend, and a complete DevOps
pipeline.

| Metric | Value |
|--------|-------|
| Python source lines | 6,566 |
| TypeScript/TSX lines | 3,636 |
| Backend modules | 28 files |
| Test files | 11 files |
| Total test cases | 322 |
| Python dependencies | 25 packages |
| LangGraph nodes | 6 |
| API endpoints | 8 |
| CI/CD workflows | 3 |

---

## 2. Project Structure

```
parking-chatbot/
├── .github/
│   └── workflows/
│       ├── backend-ci.yml
│       ├── docker-build.yml
│       └── frontend-ci.yml
├── .mypy_cache/
│   ├── 3.11/
│   │   ├── cache.0.db
│   │   ├── cache.1.db
│   │   ├── cache.10.db
│   │   ├── cache.11.db
│   │   ├── cache.12.db
│   │   ├── cache.13.db
│   │   ├── cache.14.db
│   │   ├── cache.15.db
│   │   ├── cache.2.db
│   │   ├── cache.3.db
│   │   ├── cache.4.db
│   │   ├── cache.5.db
│   │   ├── cache.6.db
│   │   ├── cache.7.db
│   │   ├── cache.8.db
│   │   └── cache.9.db
│   ├── .gitignore
│   └── CACHEDIR.TAG
├── .pytest_cache/
│   ├── v/
│   │   └── cache/
│   ├── .gitignore
│   ├── CACHEDIR.TAG
│   └── README.md
├── config/
│   ├── __init__.py
│   └── settings.py
├── data/
│   ├── approved_reservations.txt
│   ├── parking_dynamic.db
│   └── README.md
├── frontend/
│   ├── public/
│   │   ├── file.svg
│   │   ├── globe.svg
│   │   ├── next.svg
│   │   ├── vercel.svg
│   │   └── window.svg
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── services/
│   │   ├── store/
│   │   └── types/
│   ├── .env.example
│   ├── .env.local
│   ├── .gitignore
│   ├── AGENTS.md
│   ├── CLAUDE.md
│   ├── components.json
│   ├── Dockerfile
│   ├── eslint.config.mjs
│   ├── next-env.d.ts
│   ├── next.config.ts
│   ├── package-lock.json
│   ├── package.json
│   ├── postcss.config.mjs
│   ├── README.md
│   ├── tsconfig.json
│   └── tsconfig.tsbuildinfo
├── logs/
│   ├── access.log
│   ├── app.log
│   └── error.log
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   └── admin_agent.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── server.py
│   ├── chatbot/
│   │   ├── __init__.py
│   │   ├── chatbot.py
│   │   ├── guardrails.py
│   │   └── rag_chain.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── load_data.py
│   │   └── parking_info.txt
│   ├── database/
│   │   ├── __init__.py
│   │   ├── sql_store.py
│   │   └── vector_store.py
│   ├── evaluation/
│   │   ├── __init__.py
│   │   └── evaluator.py
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── nodes.py
│   │   ├── pipeline.py
│   │   └── state.py
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── mcp_client.py
│   │   └── mcp_server.py
│   ├── notifications/
│   │   ├── __init__.py
│   │   └── email_service.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logging_config.py
│   │   └── masking.py
│   └── __init__.py
├── terraform/
│   ├── main.tf
│   ├── outputs.tf
│   ├── provider.tf
│   └── variables.tf
├── tests/
│   ├── __init__.py
│   ├── test_admin_agent.py
│   ├── test_api_server.py
│   ├── test_chatbot.py
│   ├── test_email_service.py
│   ├── test_evaluator.py
│   ├── test_graph.py
│   ├── test_guardrails.py
│   ├── test_masking.py
│   ├── test_mcp.py
│   ├── test_sql_store.py
│   └── test_vector_store.py
├── .coverage
├── .dockerignore
├── .env
├── .env.example
├── .flake8
├── .gitignore
├── AGENTS.md
├── coverage.xml
├── create_stage4_implementation.py
├── create_stage4_presentation.py
├── DEPLOYMENT.md
├── docker-compose.yml
├── Dockerfile
├── main.py
├── MIGRATION_CHROMADB_TO_PINECONE.md
├── ParkSmart_Stage4_Presentation.pptx
├── pyproject.toml
├── pytest.ini
├── README.md
├── requirements.txt
├── show_tables.py
├── test_graph_live.py
└── view_db.py
```

---

## 3. Technology Choices

### Why Each Technology Was Chosen

| Technology | Why Chosen | Alternatives Considered |
|-----------|-----------|------------------------|
| **LangChain** | Industry-standard LLM framework with built-in RAG patterns, prompt templates, and tool calling | LlamaIndex (less flexible), raw OpenAI SDK (too low-level) |
| **LangGraph** | Native state-graph orchestration with conditional edges, human-in-the-loop support, and TypedDict state | Prefect (too heavy), custom FSM (no ecosystem) |
| **FastAPI** | Async Python web framework with automatic OpenAPI docs, Pydantic validation, and high performance | Flask (no async, no auto-docs), Django (too heavyweight) |
| **Pinecone** | Managed vector database with serverless deployment, zero-ops, and built-in similarity search | ChromaDB (local only), Weaviate (self-hosted complexity) |
| **HuggingFace Embeddings** | Free local embedding model (`all-MiniLM-L6-v2`), no API key needed, 384-dim vectors | OpenAI Embeddings (costly), Cohere (API dependency) |
| **SQLAlchemy + SQLite** | Lightweight ORM with zero-config database for transactional data (reservations, prices) | PostgreSQL (overkill for demo), raw SQL (unmaintainable) |
| **Presidio** | Microsoft's PII detection engine with spaCy NER for enterprise-grade privacy protection | Regex-only (misses edge cases), AWS Comprehend (cloud cost) |
| **Next.js 16** | React framework with App Router, Server Components, and built-in optimizations | Create React App (deprecated), Vite (no SSR) |
| **Zustand** | Minimal state management (2KB) with no boilerplate, perfect for chat session state | Redux (too verbose), Jotai (atomic model overkill) |
| **shadcn/ui** | Copy-paste component library built on Radix UI primitives with Tailwind styling | Material UI (heavy bundle), Chakra UI (different styling paradigm) |
| **Docker** | Containerization with multi-stage builds for reproducible, secure deployments | Podman (less tooling), direct VM deployment (not portable) |
| **GitHub Actions** | Native CI/CD integrated with the repository, free for public repos | Jenkins (self-hosted), CircleCI (separate service) |
| **Terraform** | Declarative IaC for reproducible cloud infrastructure provisioning | Pulumi (imperative), CloudFormation (AWS-only) |

---

## 4. Backend Modules

### REST API Layer (`src/api/`)

Handles HTTP requests, chat endpoint, reservation CRUD, and admin actions

**`src\api\server.py`** (369 lines)
  - *REST API Server - Communication Bridge Between User Chatbot and Admin.*
  - Classes: `ReservationRequest`, `ReservationResponse`, `AdminActionRequest`, `StatusResponse`, `ChatRequest`, `ChatResponse`
  - Functions: `chat`, `health_check`, `health_check_detailed`, `create_reservation`, `list_reservations`, `get_reservation`, `approve_reservation`, `reject_reservation`

### Chat Engine (`src/chatbot/`)

Conversation state machine, RAG chain, and guardrails for PII/injection protection

**`src\chatbot\chatbot.py`** (372 lines)
  - *Main Chatbot Module - Orchestrates conversation flow.*
  - Classes: `ConversationState`, `ReservationData`, `ParkingChatbot`
  - Functions: `is_complete`, `to_dict`, `summary`, `chat`, `get_reservation_data`, `reset`

**`src\chatbot\guardrails.py`** (246 lines)
  - *Guardrails Module - Data Protection and Safety Filtering.*
  - Classes: `Guardrails`
  - Functions: `check_input`, `filter_output`, `detect_pii_in_text`

**`src\chatbot\rag_chain.py`** (178 lines)
  - *RAG Chain Module - The core intelligence of the chatbot.*
  - Classes: `RAGChain`
  - Functions: `format_docs`, `get_dynamic_context`, `ask`, `get_relevant_documents`, `clear_history`, `get_retrieval_context`

### Data Layer (`src/database/`)

Dual database architecture — SQLite for transactions, Pinecone for semantic search

**`src\database\sql_store.py`** (460 lines)
  - *SQL Store Module - SQLite Database for Dynamic Parking Data.*
  - Classes: `WorkingHours`, `ParkingPrice`, `ParkingAvailability`, `Reservation`, `SQLStore`
  - Functions: `initialize_default_data`, `get_working_hours`, `get_prices`, `get_availability`, `get_total_availability`, `get_dynamic_context`, `save_reservation`, `get_reservations`, `get_reservation_by_id`, `update_reservation_status`

**`src\database\vector_store.py`** (243 lines)
  - *Vector Store Module - Pinecone Integration for RAG.*
  - Classes: `VectorStoreError`, `VectorStoreConnectionError`, `VectorStore`
  - Functions: `validate_connection`, `add_documents`, `similarity_search`, `similarity_search_with_score`, `get_retriever`, `get_collection_count`, `clear`

### LangGraph Pipeline (`src/graph/`)

StateGraph orchestration with 6 nodes, conditional edges, and human-in-the-loop

**`src\graph\nodes.py`** (373 lines)
  - *LangGraph Nodes — Individual Processing Steps in the Pipeline.*
  - Functions: `initialize_components`, `user_interaction_node`, `save_reservation_node`, `admin_review_node`, `notification_node`, `mcp_recording_node`, `completion_node`

**`src\graph\pipeline.py`** (280 lines)
  - *LangGraph Pipeline Builder — Wires Nodes Together into a State Graph.*
  - Functions: `after_user_interaction`, `after_admin_review`, `after_notification`, `create_pipeline`, `create_initial_state`, `run_user_message`, `run_admin_decision`

**`src\graph\state.py`** (81 lines)
  - *LangGraph State Schema — Defines the Data Flowing Through the Graph.*
  - Classes: `PipelinePhase`, `GraphState`

### Admin Agent (`src/agents/`)

LangChain agent with tools for reservation review via CLI

**`src\agents\admin_agent.py`** (381 lines)
  - *Admin Agent Module - Human-in-the-Loop Reservation Approval.*
  - Classes: `AdminAgent`
  - Functions: `create_check_availability_tool`, `check_availability`, `create_get_reservation_tool`, `get_reservation`, `create_list_pending_tool`, `list_pending_reservations`, `get_pending_reservations`, `review_reservation`, `approve_reservation`, `reject_reservation`...

### Email Service (`src/notifications/`)

SMTP notifications with HTML templates, retry logic, and console fallback

**`src\notifications\email_service.py`** (497 lines)
  - *Email Notification Service — Enterprise-Grade SMTP Integration.*
  - Classes: `EmailServiceError`, `EmailService`
  - Functions: `send_email`, `notify_new_reservation`, `send_user_approval`, `send_user_rejection`, `notify_user_status_change`

### MCP Integration (`src/mcp/`)

Model Context Protocol server and client for tool-based reservation recording

**`src\mcp\mcp_client.py`** (223 lines)
  - *MCP Client — Connects agents to the MCP Server.*
  - Classes: `MCPClient`
  - Functions: `is_server_available`, `list_tools`, `call_tool`, `write_reservation_to_file`, `read_approved_reservations`

**`src\mcp\mcp_server.py`** (259 lines)
  - *MCP Server — Model Context Protocol Server for Parking Reservations.*
  - Classes: `ToolParameter`, `ToolDefinition`, `ToolsListResponse`, `ToolCallRequest`, `ToolCallResponse`
  - Functions: `verify_api_key`, `tool_write_reservation_to_file`, `tool_read_approved_reservations`, `mcp_health`, `list_tools`, `call_tool`

### Utilities (`src/utils/`)

Email masking, structured logging configuration

**`src\utils\logging_config.py`** (71 lines)
  - *Production Logging Configuration for ParkSmart.*
  - Functions: `setup_logging`

**`src\utils\masking.py`** (54 lines)
  - *Masking Utilities — Protect PII in terminal output and logs.*
  - Functions: `mask_email`, `validate_email`

---

## 5. Frontend Modules

The frontend is a **Next.js 16** application using the App Router pattern.

### Routes & Layouts (`frontend/src/app/`)

- `frontend\src\app\admin\page.tsx` (108 lines)
- `frontend\src\app\chat\page.tsx` (76 lines)
- `frontend\src\app\layout.tsx` (38 lines)
- `frontend\src\app\page.tsx` (4 lines)

### UI Components (`frontend/src/components/`)

- `frontend\src\components\admin\ActivityFeed.tsx` (99 lines)
- `frontend\src\components\admin\AdminLoginGate.tsx` (163 lines)
- `frontend\src\components\admin\ReservationModal.tsx` (148 lines)
- `frontend\src\components\admin\ReservationTable.tsx` (163 lines)
- `frontend\src\components\admin\StatsCards.tsx` (84 lines)
- `frontend\src\components\chat\ChatInput.tsx` (65 lines)
- `frontend\src\components\chat\ChatMessage.tsx` (65 lines)
- `frontend\src\components\chat\ChatSidebar.tsx` (87 lines)
- `frontend\src\components\chat\ChatWindow.tsx` (60 lines)
- `frontend\src\components\chat\ReservationModal.tsx` (228 lines)
- `frontend\src\components\chat\TypingIndicator.tsx` (35 lines)
- `frontend\src\components\providers\Providers.tsx` (19 lines)
- `frontend\src\components\shared\EmptyState.tsx` (19 lines)
- `frontend\src\components\shared\ErrorBoundary.tsx` (44 lines)
- `frontend\src\components\shared\Navbar.tsx` (66 lines)
- `frontend\src\components\shared\StatusBadge.tsx` (22 lines)
- `frontend\src\components\shared\ThemeToggle.tsx` (34 lines)
- `frontend\src\components\ui\avatar.tsx` (100 lines)
- `frontend\src\components\ui\badge.tsx` (48 lines)
- `frontend\src\components\ui\button.tsx` (54 lines)
- `frontend\src\components\ui\card.tsx` (94 lines)
- `frontend\src\components\ui\dialog.tsx` (147 lines)
- `frontend\src\components\ui\dropdown-menu.tsx` (250 lines)
- `frontend\src\components\ui\input.tsx` (17 lines)
- `frontend\src\components\ui\label.tsx` (16 lines)
- `frontend\src\components\ui\scroll-area.tsx` (50 lines)
- `frontend\src\components\ui\select.tsx` (188 lines)
- `frontend\src\components\ui\separator.tsx` (21 lines)
- `frontend\src\components\ui\sheet.tsx` (125 lines)
- `frontend\src\components\ui\skeleton.tsx` (11 lines)
- `frontend\src\components\ui\table.tsx` (105 lines)
- `frontend\src\components\ui\tabs.tsx` (74 lines)
- `frontend\src\components\ui\textarea.tsx` (15 lines)
- `frontend\src\components\ui\tooltip.tsx` (59 lines)

### State Management (`frontend/src/store/`)

- `frontend\src\store\adminStore.ts` (107 lines)
- `frontend\src\store\authStore.ts` (50 lines)
- `frontend\src\store\chatStore.ts` (127 lines)
- `frontend\src\store\uiStore.ts` (15 lines)

### API Services (`frontend/src/services/`)

- `frontend\src\services\adminService.ts` (34 lines)
- `frontend\src\services\chatService.ts` (9 lines)
- `frontend\src\services\reservationService.ts` (21 lines)

### Custom Hooks (`frontend/src/hooks/`)

- `frontend\src\hooks\useAutoScroll.ts` (14 lines)
- `frontend\src\hooks\useMediaQuery.ts` (16 lines)

### TypeScript Types (`frontend/src/types/`)

- `frontend\src\types\index.ts` (85 lines)

### Utility Functions (`frontend/src/lib/`)

- `frontend\src\lib\api.ts` (21 lines)
- `frontend\src\lib\helpers.ts` (76 lines)
- `frontend\src\lib\utils.ts` (5 lines)
- `frontend\src\lib\validations.ts` (44 lines)

---

## 6. LangGraph Orchestration

### Architecture

The LangGraph StateGraph replaces manual multi-terminal orchestration with a
single-process pipeline that routes between 6 nodes using conditional edges.

```
┌──────────────────┐
│ user_interaction  │ ← Entry point (all messages start here)
└────────┬─────────┘
         │
   booking complete?
   ├── No ──► END (return Q&A response to user)
   └── Yes
         │
┌────────▼─────────┐
│ save_reservation  │ ← Persist to SQLite, set phase = AWAITING_ADMIN
└────────┬─────────┘
         │
┌────────▼─────────┐
│  admin_review     │ ← HUMAN-IN-THE-LOOP: graph pauses here
└───┬──────────┬───┘
    │          │
 approve    reject
    │          │
┌───▼──┐   ┌──▼───┐
│notify│   │notify │ ← Update DB status + send email
└───┬──┘   └──┬───┘
    │          │
┌───▼──┐       │
│ MCP  │       │     ← Write to file (approvals only)
└───┬──┘       │
    │          │
┌───▼──────────▼───┐
│    completion     │ ← Generate pipeline summary
└──────────────────┘
```

### State Schema (`GraphState`)

Every node receives the full state and returns only changed fields:

| Field | Type | Purpose |
|-------|------|---------|
| `user_message` | `str` | Current user input |
| `bot_response` | `str` | Chatbot response to display |
| `conversation_phase` | `PipelinePhase` | Current phase (10 values) |
| `reservation_data` | `dict` | Collected booking fields |
| `reservation_id` | `int` | Database ID after save |
| `admin_decision` | `str` | "approve" or "reject" |
| `admin_notes` | `str` | Admin's reason/notes |
| `notification_sent` | `bool` | Email sent successfully |
| `mcp_recorded` | `bool` | MCP file write succeeded |
| `error` | `str` | Error message if failed |
| `history` | `list` | Conversation history tuples |
| `is_booking_flow` | `bool` | Mid-booking indicator |
| `needs_admin_input` | `bool` | Graph waiting for admin |
| `admin_input` | `str` | Admin's command string |

### Conditional Edge Functions

| Function | After Node | Routes To |
|----------|-----------|-----------|
| `after_user_interaction` | `user_interaction` | `save_reservation` (booking done) or `END` (Q&A) |
| `after_admin_review` | `admin_review` | `notification` (decided) or `END` (waiting) |
| `after_notification` | `notification` | `mcp_recording` (approved) or `completion` (rejected) |

---

## 7. RAG Pipeline

### How It Works

1. **User submits a question** (e.g., "What are parking rates?")
2. **Embed the query** using HuggingFace `all-MiniLM-L6-v2` (local, no API cost)
3. **Search Pinecone** for top-K most similar document chunks
4. **Augment the prompt** with retrieved context + dynamic SQL data (prices, hours)
5. **Generate response** via GPT-4o through EPAM DIAL proxy
6. **Apply guardrails** — check output for leaked PII, redact if found

### Dual Data Sources

| Source | Type | Data | Access |
|--------|------|------|--------|
| Pinecone | Vector DB | Location, facilities, policies, booking rules | Semantic similarity search |
| SQLite | Relational DB | Current prices, hours, availability counts | Direct SQL queries |

Both sources are merged into the LLM prompt so answers reflect both static
knowledge and real-time data.

---

## 8. Human-in-the-Loop Workflow

### Why Human Review?

Automated booking without oversight risks double-bookings, fraudulent
reservations, or capacity violations. The admin review step ensures a human
validates every reservation before confirmation.

### How It Works

```
User completes booking
       │
       ▼
save_reservation (DB insert, status: pending)
       │
       ▼
admin_review node (graph PAUSES)
       │
       ├──► CLI: prompt switches from "👤 You:" to "🔧 Admin:"
       └──► Web: admin opens /admin dashboard
       │
Admin types "approve [notes]" or "reject [reason]"
       │
       ▼
Pipeline RESUMES automatically
       │
       ▼
notification → mcp_recording → completion
```

### Implementation Detail

The `admin_review` node sets `needs_admin_input = True` in the state.
The conditional edge function `after_admin_review` returns `END` when this
flag is set, pausing the graph. When the admin provides input,
`run_admin_decision()` re-invokes the graph starting at `admin_review`
with the admin's decision populated in the state.

---

## 9. Request Flow Analysis

### Chat Message Flow (Frontend → Backend → Response)

```
Browser (Next.js)
    │
    │  POST /api/chat  { "message": "What are parking rates?" }
    ▼
FastAPI Server (server.py)
    │
    │  run_user_message(pipeline, message, state)
    ▼
LangGraph Pipeline
    │
    │  user_interaction node
    ▼
ParkingChatbot.process_message()
    │
    ├── Is it a booking flow? → Collect next field
    │
    └── General Q&A? → RAG Chain
            │
            ├── Embed query (HuggingFace)
            ├── Search Pinecone (top-5)
            ├── Query SQLite (prices, hours)
            ├── Build prompt (system + context + query)
            ├── Call GPT-4o (EPAM DIAL)
            └── Apply guardrails (PII check)
    │
    ▼
Response returned to frontend
    │
    ▼
ChatWindow renders MessageBubble
```

### Reservation Submission Flow

```
User confirms booking details
    │
    ▼
Chatbot.process_message() detects confirmation
    │
    ▼
POST /api/reservations (auto-submitted by chatbot)
    │
    ▼
SQLStore.create_reservation() → DB insert (status: pending)
    │
    ▼
EmailService.send_admin_notification()
    │
    ▼
Response: "Reservation submitted! Waiting for admin approval."
```

---

## 10. Admin Approval Flow

### Via Web Dashboard

```
Admin navigates to /admin → AdminLoginGate (username/password)
    │
    ▼
GET /api/reservations?status=pending → ReservationTable renders
    │
    ▼
Admin clicks "Approve" or "Reject" → enters optional notes
    │
    ▼
PUT /api/reservations/{id}/approve (or /reject)
    │
    ▼
SQLStore updates status + admin_notes + approved_at/rejected_at
    │
    ▼
EmailService sends notification to user
    │
    ▼
Table auto-refreshes with updated status
```

### Via CLI Agent

```
python main.py --admin
    │
    ▼
admin> list          → GET /api/reservations?status=pending
admin> review 1      → GET /api/reservations/1 + availability check
admin> approve 1 OK  → PUT /api/reservations/1/approve
admin> reject 2 Full → PUT /api/reservations/2/reject
```

---

## 11. Vector Search Flow

```
User: "Do you have EV charging stations?"
         │
         ▼
    Embed query → [0.23, -0.15, 0.87, ...] (384-dim vector)
         │
         ▼
    Pinecone.query(vector, top_k=5)
         │
         ▼
    Returns ranked document chunks:
      1. "EV Charging: 15 Level 2 stations..." (score: 0.92)
      2. "Parking facilities include..." (score: 0.85)
      3. "Green parking initiative..." (score: 0.78)
         │
         ▼
    Concatenate as context for LLM prompt
         │
         ▼
    GPT-4o generates answer using retrieved context
         │
         ▼
    "Yes! ParkSmart has 15 Level 2 and 5 DC fast charging stations..."
```

### Why This Architecture Works

- **Semantic search** finds relevant info even when user phrasing differs
- **Local embeddings** (HuggingFace) avoid API costs for every query
- **Pinecone serverless** scales automatically with zero infrastructure
- **Dynamic SQL data** supplements static knowledge with real-time pricing

---

## 12. Notification Flow

### Email Delivery Pipeline

```
Trigger Event (new booking / approve / reject)
       │
       ▼
EmailService.send_notification()
       │
       ├── Build HTML email template
       │     └── Subject, body, reservation details
       │
       ├── Connect to SMTP server
       │     ├── Try SSL (port 465)
       │     └── Fallback to STARTTLS (port 587)
       │
       ├── Send with retry (tenacity)
       │     └── 3 attempts, exponential backoff
       │
       ├── Success → notification_sent = True
       │
       └── Failure → Console fallback
             └── Print notification to stdout
             └── notification_sent = True (degraded)
```

### Email Types

| Event | Recipient | Content |
|-------|-----------|---------|
| New reservation | Admin | Reservation details, review link |
| Approved | User | Confirmation with booking summary |
| Rejected | User | Rejection with admin's reason |

### Security

- Email addresses masked in logs: `sa****@gmail.com`
- SMTP credentials from environment variables (never hardcoded)
- App-specific passwords recommended for Gmail

---

## 13. Docker Setup

| File | Exists | Purpose |
|------|--------|---------|
| `Dockerfile` | Yes | Multi-stage backend build |
| `frontend/Dockerfile` | Yes | Frontend production build |
| `docker-compose.yml` | Yes | Service orchestration |

### Backend Dockerfile Strategy

- **Stage 1 (Builder):** Install all Python deps + spaCy model in a virtualenv
- **Stage 2 (Runtime):** Copy only the virtualenv and app code into a slim image
- **Security:** Runs as non-root `parksmart` user
- **Health check:** Polls `/api/health` every 30 seconds

### Docker Compose Services

| Service | Image | Port | Depends On |
|---------|-------|------|------------|
| `backend` | `Dockerfile` | 8000 | — |
| `frontend` | `frontend/Dockerfile` | 3000 | backend (healthy) |

---

## 14. CI/CD Pipeline

### Workflow Files

| File |
|------|
| `backend-ci.yml` |
| `docker-build.yml` |
| `frontend-ci.yml` |

### Backend CI Pipeline

```
Push to main (src/**, tests/**, requirements.txt)
    │
    ▼
Job 1: Lint & Format Check
    ├── Black (formatting)
    ├── isort (import ordering)
    ├── flake8 (style violations)
    └── mypy (type checking, non-blocking)
    │
    ▼
Job 2: Test Suite
    ├── Install dependencies + spaCy model
    ├── Run 161 pytest tests with coverage
    └── Upload coverage report
    │
    ▼
Job 3: Validate FastAPI Startup
    └── Start uvicorn, health check, stop
```

### Frontend CI Pipeline

```
Push to main (frontend/**)
    │
    ▼
Job 1: Lint & TypeScript
    ├── ESLint
    └── tsc --noEmit
    │
    ▼
Job 2: Production Build
    └── next build
```

### Docker Build & Validate Pipeline

```
Push to main (Dockerfile, docker-compose.yml, terraform/**)
    │
    ▼
Jobs 1-2: Build Backend + Frontend Images (parallel)
    │
    ▼
Job 3: Validate Docker Compose
    ├── docker compose build
    ├── docker compose up -d
    ├── Health check verification
    └── docker compose down
    │
    ▼
Job 4: Validate Terraform
    ├── terraform fmt -check
    ├── terraform init
    └── terraform validate
```

---

## 15. Terraform Infrastructure

### Files

| File | Lines |
|------|-------|
| `main.tf` | 37 |
| `outputs.tf` | 23 |
| `provider.tf` | 27 |
| `variables.tf` | 83 |

### Resources Provisioned

| Resource | Provider | Purpose |
|----------|----------|---------|
| `render_web_service.backend` | Render | FastAPI backend hosting |
| Vercel (manual) | Vercel CLI | Next.js frontend hosting |

### Deployment Flow

```
terraform init → terraform plan → terraform apply
    │
    ▼
Render provisions a web service:
  - Build: pip install + spaCy download + DB setup
  - Start: uvicorn on $PORT
  - Health check: /api/health
  - Environment variables injected via TF_VAR_*
```

---

## 16. Testing Summary

### Test Breakdown

| File | Module | Tests |
|------|--------|-------|
| `test_admin_agent.py` | admin_agent | 18 |
| `test_api_server.py` | api_server | 22 |
| `test_chatbot.py` | chatbot | 24 |
| `test_email_service.py` | email_service | 40 |
| `test_evaluator.py` | evaluator | 12 |
| `test_graph.py` | graph | 76 |
| `test_guardrails.py` | guardrails | 16 |
| `test_masking.py` | masking | 34 |
| `test_mcp.py` | mcp | 42 |
| `test_sql_store.py` | sql_store | 18 |
| `test_vector_store.py` | vector_store | 20 |
| **Total** | | **322** |

### Testing Strategy

- **Unit tests**: Each module tested in isolation with mocked dependencies
- **Integration tests**: Pipeline E2E tests with all nodes connected
- **Mocking**: All external services (LLM, Pinecone, SMTP) are mocked
- **Database**: In-memory SQLite (`sqlite:///:memory:`) — no cleanup needed
- **Async**: `@pytest.mark.asyncio` for async endpoint tests
- **Configuration**: Mock `settings` object, not `os.environ`
- **CI**: Tests run automatically on every push via GitHub Actions

---

## 17. Code Metrics

### Backend Source Files

| File | Lines |
|------|-------|
| `src\__init__.py` | 1 |
| `src\agents\__init__.py` | 0 |
| `src\agents\admin_agent.py` | 381 |
| `src\api\__init__.py` | 0 |
| `src\api\server.py` | 369 |
| `src\chatbot\__init__.py` | 1 |
| `src\chatbot\chatbot.py` | 372 |
| `src\chatbot\guardrails.py` | 246 |
| `src\chatbot\rag_chain.py` | 178 |
| `src\data\__init__.py` | 1 |
| `src\data\load_data.py` | 86 |
| `src\database\__init__.py` | 1 |
| `src\database\sql_store.py` | 460 |
| `src\database\vector_store.py` | 243 |
| `src\evaluation\__init__.py` | 1 |
| `src\evaluation\evaluator.py` | 250 |
| `src\graph\__init__.py` | 1 |
| `src\graph\nodes.py` | 373 |
| `src\graph\pipeline.py` | 280 |
| `src\graph\state.py` | 81 |
| `src\mcp\__init__.py` | 1 |
| `src\mcp\mcp_client.py` | 223 |
| `src\mcp\mcp_server.py` | 259 |
| `src\notifications\__init__.py` | 0 |
| `src\notifications\email_service.py` | 497 |
| `src\utils\__init__.py` | 1 |
| `src\utils\logging_config.py` | 71 |
| `src\utils\masking.py` | 54 |
| **Subtotal** | **4431** |

### Other Python

| Category | Lines |
|----------|-------|
| Test files | 2066 |
| Config | 69 |
| **Total Python** | **6566** |

---

*Report generated by `create_stage4_implementation.py`*
