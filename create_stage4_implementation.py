"""
Stage 4 Implementation Report Generator.

Scans the ParkSmart project structure, analyzes architecture, and generates
a comprehensive Markdown implementation report suitable for:
  - Technical reviewers and evaluators
  - Recruiters assessing portfolio projects
  - Internship/assessment submissions

Usage:
    python create_stage4_implementation.py

Output:
    IMPLEMENTATION_REPORT.md — full project analysis with architecture,
    module descriptions, technology justifications, and workflow diagrams.
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ── Configuration ──
PROJECT_ROOT = Path(__file__).parent
OUTPUT_FILE = PROJECT_ROOT / "IMPLEMENTATION_REPORT.md"

# Directories to scan
SRC_DIR = PROJECT_ROOT / "src"
TESTS_DIR = PROJECT_ROOT / "tests"
CONFIG_DIR = PROJECT_ROOT / "config"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
GITHUB_DIR = PROJECT_ROOT / ".github"
TERRAFORM_DIR = PROJECT_ROOT / "terraform"


# ════════════════════════════════════════════
# UTILITY FUNCTIONS
# ════════════════════════════════════════════


def count_lines(filepath: Path) -> int:
    """Count non-blank lines in a file."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for line in f if line.strip())
    except (OSError, UnicodeDecodeError):
        return 0


def count_python_lines(directory: Path) -> dict:
    """Count lines of Python code in a directory, grouped by file."""
    results = {}
    if not directory.exists():
        return results
    for py_file in sorted(directory.rglob("*.py")):
        if "__pycache__" in str(py_file):
            continue
        rel = py_file.relative_to(PROJECT_ROOT)
        results[str(rel)] = count_lines(py_file)
    return results


def extract_classes_and_functions(filepath: Path) -> dict:
    """Extract class and function names from a Python file."""
    classes = []
    functions = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("class "):
                    match = re.match(r"class\s+(\w+)", stripped)
                    if match:
                        classes.append(match.group(1))
                elif stripped.startswith("def "):
                    match = re.match(r"def\s+(\w+)", stripped)
                    if match:
                        functions.append(match.group(1))
    except (OSError, UnicodeDecodeError):
        pass
    return {"classes": classes, "functions": functions}


def extract_docstring(filepath: Path) -> str:
    """Extract the module-level docstring from a Python file."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        match = re.match(r'^(?:\s*#[^\n]*\n)*\s*"""(.*?)"""', content, re.DOTALL)
        if match:
            return match.group(1).strip().split("\n")[0]
        match = re.match(r"^(?:\s*#[^\n]*\n)*\s*'''(.*?)'''", content, re.DOTALL)
        if match:
            return match.group(1).strip().split("\n")[0]
    except (OSError, UnicodeDecodeError):
        pass
    return ""


def count_tests(test_dir: Path) -> dict:
    """Count test functions per test file."""
    results = {}
    if not test_dir.exists():
        return results
    for py_file in sorted(test_dir.glob("test_*.py")):
        funcs = extract_classes_and_functions(py_file)
        test_count = len([f for f in funcs["functions"] if f.startswith("test_")])
        # Also count methods inside test classes
        try:
            with open(py_file, "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    if line.strip().startswith("def test_") and "self" in line:
                        test_count += 1
        except (OSError, UnicodeDecodeError):
            pass
        results[py_file.name] = test_count
    return results


def build_tree(directory: Path, prefix: str = "", max_depth: int = 4, current_depth: int = 0) -> str:
    """Generate a directory tree string."""
    if current_depth >= max_depth or not directory.exists():
        return ""

    lines = []
    entries = sorted(directory.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    # Skip hidden/generated directories
    skip = {"__pycache__", "node_modules", ".next", ".git", "venv", ".venv", "chroma_db"}
    entries = [e for e in entries if e.name not in skip]

    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        if entry.is_dir():
            lines.append(f"{prefix}{connector}{entry.name}/")
            extension = "    " if is_last else "│   "
            lines.append(build_tree(entry, prefix + extension, max_depth, current_depth + 1))
        else:
            lines.append(f"{prefix}{connector}{entry.name}")
    return "\n".join(line for line in lines if line)


def get_requirements() -> list:
    """Parse requirements.txt into a list of package names."""
    req_file = PROJECT_ROOT / "requirements.txt"
    if not req_file.exists():
        return []
    packages = []
    with open(req_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                name = re.split(r"[>=<\[]", line)[0].strip()
                if name:
                    packages.append(name)
    return packages


# ════════════════════════════════════════════
# REPORT SECTIONS
# ════════════════════════════════════════════


def section_header() -> str:
    return f"""# ParkSmart — Stage 4 Implementation Report

> **Auto-generated** on {datetime.now().strftime("%B %d, %Y at %H:%M")}
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
"""


def section_executive_summary() -> str:
    # Count total lines
    backend_lines = count_python_lines(SRC_DIR)
    test_lines = count_python_lines(TESTS_DIR)
    config_lines = count_python_lines(CONFIG_DIR)
    total_py = sum(backend_lines.values()) + sum(test_lines.values()) + sum(config_lines.values())

    # Count frontend files
    frontend_ts = 0
    if FRONTEND_DIR.exists():
        for ext in ("*.ts", "*.tsx"):
            for f in FRONTEND_DIR.rglob(ext):
                if "node_modules" not in str(f) and ".next" not in str(f):
                    frontend_ts += count_lines(f)

    test_counts = count_tests(TESTS_DIR)
    total_tests = sum(test_counts.values())
    packages = get_requirements()

    return f"""## 1. Executive Summary

ParkSmart is a **full-stack AI parking reservation platform** built across four
iterative development stages. It combines a LangChain RAG chatbot with LangGraph
orchestration, a FastAPI REST backend, a Next.js frontend, and a complete DevOps
pipeline.

| Metric | Value |
|--------|-------|
| Python source lines | {total_py:,} |
| TypeScript/TSX lines | {frontend_ts:,} |
| Backend modules | {len(backend_lines)} files |
| Test files | {len(test_counts)} files |
| Total test cases | {total_tests} |
| Python dependencies | {len(packages)} packages |
| LangGraph nodes | 6 |
| API endpoints | 8 |
| CI/CD workflows | 3 |

---
"""


def section_project_structure() -> str:
    tree = build_tree(PROJECT_ROOT, max_depth=3)
    return f"""## 2. Project Structure

```
parking-chatbot/
{tree}
```

---
"""


def section_technology_choices() -> str:
    return """## 3. Technology Choices

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
"""


def section_backend_modules() -> str:
    lines = []
    lines.append("## 4. Backend Modules\n")

    module_map = {
        "src/api": ("REST API Layer", "Handles HTTP requests, chat endpoint, reservation CRUD, and admin actions"),
        "src/chatbot": ("Chat Engine", "Conversation state machine, RAG chain, and guardrails for PII/injection protection"),
        "src/database": ("Data Layer", "Dual database architecture — SQLite for transactions, Pinecone for semantic search"),
        "src/graph": ("LangGraph Pipeline", "StateGraph orchestration with 6 nodes, conditional edges, and human-in-the-loop"),
        "src/agents": ("Admin Agent", "LangChain agent with tools for reservation review via CLI"),
        "src/notifications": ("Email Service", "SMTP notifications with HTML templates, retry logic, and console fallback"),
        "src/mcp": ("MCP Integration", "Model Context Protocol server and client for tool-based reservation recording"),
        "src/utils": ("Utilities", "Email masking, structured logging configuration"),
    }

    for module_path, (title, description) in module_map.items():
        full_path = PROJECT_ROOT / module_path
        if not full_path.exists():
            continue

        lines.append(f"### {title} (`{module_path}/`)\n")
        lines.append(f"{description}\n")

        py_files = sorted(full_path.glob("*.py"))
        for py_file in py_files:
            if py_file.name == "__init__.py":
                continue
            rel = py_file.relative_to(PROJECT_ROOT)
            docstring = extract_docstring(py_file)
            symbols = extract_classes_and_functions(py_file)
            loc = count_lines(py_file)

            lines.append(f"**`{rel}`** ({loc} lines)")
            if docstring:
                lines.append(f"  - *{docstring}*")
            if symbols["classes"]:
                lines.append(f"  - Classes: `{'`, `'.join(symbols['classes'])}`")
            if symbols["functions"]:
                public = [f for f in symbols["functions"] if not f.startswith("_")]
                if public:
                    lines.append(f"  - Functions: `{'`, `'.join(public[:10])}`{'...' if len(public) > 10 else ''}")
            lines.append("")

    return "\n".join(lines) + "\n---\n"


def section_frontend_modules() -> str:
    if not FRONTEND_DIR.exists():
        return "## 5. Frontend Modules\n\nFrontend directory not found.\n\n---\n"

    lines = []
    lines.append("## 5. Frontend Modules\n")
    lines.append("The frontend is a **Next.js 16** application using the App Router pattern.\n")

    sections = {
        "frontend/src/app": "Routes & Layouts",
        "frontend/src/components": "UI Components",
        "frontend/src/store": "State Management",
        "frontend/src/services": "API Services",
        "frontend/src/hooks": "Custom Hooks",
        "frontend/src/types": "TypeScript Types",
        "frontend/src/lib": "Utility Functions",
    }

    for path, title in sections.items():
        full = PROJECT_ROOT / path
        if not full.exists():
            continue

        ts_files = list(full.rglob("*.ts")) + list(full.rglob("*.tsx"))
        ts_files = [f for f in ts_files if "node_modules" not in str(f) and ".next" not in str(f)]

        if not ts_files:
            continue

        lines.append(f"### {title} (`{path}/`)\n")
        for ts_file in sorted(ts_files):
            rel = ts_file.relative_to(PROJECT_ROOT)
            loc = count_lines(ts_file)
            lines.append(f"- `{rel}` ({loc} lines)")
        lines.append("")

    return "\n".join(lines) + "\n---\n"


def section_langgraph() -> str:
    return """## 6. LangGraph Orchestration

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
"""


def section_rag_pipeline() -> str:
    return """## 7. RAG Pipeline

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
"""


def section_hitl() -> str:
    return """## 8. Human-in-the-Loop Workflow

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
"""


def section_request_flow() -> str:
    return """## 9. Request Flow Analysis

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
"""


def section_admin_flow() -> str:
    return """## 10. Admin Approval Flow

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
"""


def section_vector_search() -> str:
    return """## 11. Vector Search Flow

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
"""


def section_notification_flow() -> str:
    return """## 12. Notification Flow

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
"""


def section_docker() -> str:
    has_dockerfile = (PROJECT_ROOT / "Dockerfile").exists()
    has_compose = (PROJECT_ROOT / "docker-compose.yml").exists()
    has_frontend_dockerfile = (FRONTEND_DIR / "Dockerfile").exists()

    return f"""## 13. Docker Setup

| File | Exists | Purpose |
|------|--------|---------|
| `Dockerfile` | {"Yes" if has_dockerfile else "No"} | Multi-stage backend build |
| `frontend/Dockerfile` | {"Yes" if has_frontend_dockerfile else "No"} | Frontend production build |
| `docker-compose.yml` | {"Yes" if has_compose else "No"} | Service orchestration |

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
"""


def section_cicd() -> str:
    workflows = []
    wf_dir = GITHUB_DIR / "workflows"
    if wf_dir.exists():
        for yml in sorted(wf_dir.glob("*.yml")):
            workflows.append(yml.name)

    wf_list = "\n".join(f"| `{w}` |" for w in workflows) if workflows else "| None found |"

    return f"""## 14. CI/CD Pipeline

### Workflow Files

| File |
|------|
{wf_list}

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
"""


def section_terraform() -> str:
    tf_files = []
    if TERRAFORM_DIR.exists():
        for tf in sorted(TERRAFORM_DIR.glob("*.tf")):
            tf_files.append(tf.name)

    tf_list = "\n".join(f"| `{f}` | {count_lines(TERRAFORM_DIR / f)} |" for f in tf_files)

    return f"""## 15. Terraform Infrastructure

### Files

| File | Lines |
|------|-------|
{tf_list}

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
"""


def section_testing() -> str:
    test_counts = count_tests(TESTS_DIR)
    total = sum(test_counts.values())

    rows = []
    for filename, count in sorted(test_counts.items()):
        module = filename.replace("test_", "").replace(".py", "")
        rows.append(f"| `{filename}` | {module} | {count} |")

    table = "\n".join(rows)

    return f"""## 16. Testing Summary

### Test Breakdown

| File | Module | Tests |
|------|--------|-------|
{table}
| **Total** | | **{total}** |

### Testing Strategy

- **Unit tests**: Each module tested in isolation with mocked dependencies
- **Integration tests**: Pipeline E2E tests with all nodes connected
- **Mocking**: All external services (LLM, Pinecone, SMTP) are mocked
- **Database**: In-memory SQLite (`sqlite:///:memory:`) — no cleanup needed
- **Async**: `@pytest.mark.asyncio` for async endpoint tests
- **Configuration**: Mock `settings` object, not `os.environ`
- **CI**: Tests run automatically on every push via GitHub Actions

---
"""


def section_code_metrics() -> str:
    backend = count_python_lines(SRC_DIR)
    tests = count_python_lines(TESTS_DIR)
    config = count_python_lines(CONFIG_DIR)

    backend_total = sum(backend.values())
    tests_total = sum(tests.values())
    config_total = sum(config.values())

    rows = []
    for filepath, lines in sorted(backend.items()):
        rows.append(f"| `{filepath}` | {lines} |")

    table = "\n".join(rows)

    return f"""## 17. Code Metrics

### Backend Source Files

| File | Lines |
|------|-------|
{table}
| **Subtotal** | **{backend_total}** |

### Other Python

| Category | Lines |
|----------|-------|
| Test files | {tests_total} |
| Config | {config_total} |
| **Total Python** | **{backend_total + tests_total + config_total}** |

---

*Report generated by `create_stage4_implementation.py`*
"""


# ════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════


def generate_report() -> str:
    """Assemble all sections into the full report."""
    sections = [
        section_header(),
        section_executive_summary(),
        section_project_structure(),
        section_technology_choices(),
        section_backend_modules(),
        section_frontend_modules(),
        section_langgraph(),
        section_rag_pipeline(),
        section_hitl(),
        section_request_flow(),
        section_admin_flow(),
        section_vector_search(),
        section_notification_flow(),
        section_docker(),
        section_cicd(),
        section_terraform(),
        section_testing(),
        section_code_metrics(),
    ]
    return "\n".join(sections)


def main():
    print("Scanning project structure...")
    report = generate_report()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(report)

    line_count = report.count("\n") + 1
    print(f"Implementation report generated: {OUTPUT_FILE}")
    print(f"  {line_count} lines of Markdown")


if __name__ == "__main__":
    main()
