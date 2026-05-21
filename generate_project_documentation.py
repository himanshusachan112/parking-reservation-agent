#!/usr/bin/env python3
"""
Enterprise-Grade Technical Documentation Generator
===================================================
ParkSmart AI Parking Reservation Platform

Scans the entire project tree, inspects every folder and file, and produces
a comprehensive system-design-level document covering:

  * Architecture & system design
  * File-by-file implementation analysis
  * Technology choice rationale
  * Workflow diagrams (Mermaid)
  * CI/CD, Docker, Terraform
  * Security & testing strategies
  * Future roadmap

Output formats
--------------
1. Markdown  → PROJECT_DOCUMENTATION.md   (always)
2. PDF       → PROJECT_DOCUMENTATION.pdf   (when ``reportlab`` is installed)

Usage
-----
    python generate_project_documentation.py            # Markdown only
    python generate_project_documentation.py --pdf      # Markdown + PDF
    pip install reportlab markdown && python generate_project_documentation.py --pdf

Suitable for: recruiters, technical interviews, architecture reviews,
internship evaluations, and portfolio showcases.
"""

from __future__ import annotations

import ast
import os
import re
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_MD = PROJECT_ROOT / "PROJECT_DOCUMENTATION.md"
OUTPUT_PDF = PROJECT_ROOT / "PROJECT_DOCUMENTATION.pdf"

SKIP_DIRS = {
    "__pycache__", ".git", "node_modules", ".next", "chroma_db",
    ".mypy_cache", ".pytest_cache", "dist", "build", ".venv", "venv",
    "env", ".tox", "htmlcov", ".eggs", "*.egg-info",
}
SKIP_FILES = {".DS_Store", "Thumbs.db", ".gitkeep"}

BINARY_EXTENSIONS = {
    ".pyc", ".pyo", ".exe", ".dll", ".so", ".png", ".jpg", ".jpeg",
    ".gif", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".svg",
    ".sqlite3", ".db", ".lock",
}


# ═══════════════════════════════════════════════════════════════════════
# UTILITY HELPERS
# ═══════════════════════════════════════════════════════════════════════

def _safe_read(path: Path) -> str:
    """Read file with fallback encodings."""
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, PermissionError):
            continue
    return ""


def count_lines(path: Path) -> int:
    text = _safe_read(path)
    return len(text.splitlines()) if text else 0


def count_all_lines(root: Path, extensions: set[str]) -> int:
    total = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if Path(fn).suffix in extensions:
                total += count_lines(Path(dirpath) / fn)
    return total


def count_files(root: Path, extensions: set[str]) -> int:
    n = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if Path(fn).suffix in extensions:
                n += 1
    return n


def count_tests(tests_dir: Path) -> int:
    """Count test functions/methods (def test_*)."""
    total = 0
    if not tests_dir.exists():
        return 0
    for f in tests_dir.rglob("test_*.py"):
        text = _safe_read(f)
        total += len(re.findall(r"^\s*(?:def|async def) test_", text, re.MULTILINE))
    return total


def extract_classes(path: Path) -> List[Dict]:
    """Extract class names, methods, and docstrings from a Python file."""
    text = _safe_read(path)
    if not text:
        return []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = []
                    for a in item.args.args:
                        if a.arg != "self":
                            args.append(a.arg)
                    methods.append({
                        "name": item.name,
                        "args": args,
                        "is_async": isinstance(item, ast.AsyncFunctionDef),
                    })
            classes.append({
                "name": node.name,
                "docstring": ast.get_docstring(node) or "",
                "methods": methods,
                "lineno": node.lineno,
            })
    return classes


def extract_functions(path: Path) -> List[Dict]:
    """Extract top-level function names and docstrings."""
    text = _safe_read(path)
    if not text:
        return []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    funcs = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [a.arg for a in node.args.args]
            funcs.append({
                "name": node.name,
                "args": args,
                "docstring": ast.get_docstring(node) or "",
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "lineno": node.lineno,
            })
    return funcs


def extract_imports(path: Path) -> List[str]:
    """Extract top-level import module names."""
    text = _safe_read(path)
    if not text:
        return []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    mods: set[str] = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".")[0])
    return sorted(mods)


def build_tree(root: Path, prefix: str = "", depth: int = 0, max_depth: int = 4) -> str:
    """Build an ASCII directory tree."""
    if depth > max_depth:
        return ""
    entries = sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    lines = []
    visible = [e for e in entries if e.name not in SKIP_DIRS and e.name not in SKIP_FILES
               and not e.name.startswith(".git")]
    for i, entry in enumerate(visible):
        connector = "└── " if i == len(visible) - 1 else "├── "
        if entry.is_dir():
            lines.append(f"{prefix}{connector}{entry.name}/")
            extension = "    " if i == len(visible) - 1 else "│   "
            lines.append(build_tree(entry, prefix + extension, depth + 1, max_depth))
        else:
            if entry.suffix not in BINARY_EXTENSIONS:
                lines.append(f"{prefix}{connector}{entry.name}")
    return "\n".join(line for line in lines if line)


def get_requirements() -> List[str]:
    req_file = PROJECT_ROOT / "requirements.txt"
    if not req_file.exists():
        return []
    lines = _safe_read(req_file).splitlines()
    return [l.strip() for l in lines if l.strip() and not l.startswith("#")]


def _wrap(text: str, width: int = 90) -> str:
    return "\n".join(textwrap.fill(line, width) for line in text.splitlines())


# ═══════════════════════════════════════════════════════════════════════
# SECTION GENERATORS
# ═══════════════════════════════════════════════════════════════════════

def section_title_page() -> str:
    return f"""<div align="center">

# ParkSmart — AI Parking Reservation Platform
## Enterprise Technical Documentation

**Version:** 4.0  
**Generated:** {datetime.now().strftime("%B %d, %Y at %H:%M")}  
**Classification:** Internal / Portfolio  

---

*Full-stack AI parking reservation system featuring LangGraph orchestration,
Retrieval-Augmented Generation, human-in-the-loop admin approval,
MCP tool protocol, and enterprise CI/CD pipeline.*

</div>

---

"""


def section_table_of_contents() -> str:
    return """## Table of Contents

| # | Section | Description |
|---|---------|-------------|
| 1 | [Introduction](#1-introduction) | Project overview, objectives, and business context |
| 2 | [System Architecture](#2-system-architecture) | High-level design and component interaction |
| 3 | [Technology Choices](#3-technology-choices) | Stack rationale with alternatives considered |
| 4 | [Folder Structure](#4-folder-structure) | Complete directory layout with explanations |
| 5 | [File-by-File Explanation](#5-file-by-file-explanation) | Detailed analysis of every major file |
| 6 | [RAG Workflow](#6-rag-workflow) | Retrieval-Augmented Generation pipeline |
| 7 | [LangGraph Workflow](#7-langgraph-workflow) | State machine orchestration and node design |
| 8 | [Reservation Workflow](#8-reservation-workflow) | End-to-end booking lifecycle |
| 9 | [Frontend Architecture](#9-frontend-architecture) | Next.js component hierarchy and state management |
| 10 | [Backend Architecture](#10-backend-architecture) | FastAPI routing, services, and middleware |
| 11 | [CI/CD Pipeline](#11-cicd-pipeline) | GitHub Actions workflows and automation |
| 12 | [Docker & Deployment](#12-docker--deployment) | Containerization and production deployment |
| 13 | [Terraform](#13-terraform) | Infrastructure as Code |
| 14 | [Security](#14-security) | PII protection, guardrails, and access control |
| 15 | [Testing](#15-testing) | Test strategy, coverage, and tooling |
| 16 | [Future Enhancements](#16-future-enhancements) | Roadmap and scaling strategy |

---

"""


# ── Section 1: Introduction ──────────────────────────────────────────

def section_introduction() -> str:
    py_files = count_files(PROJECT_ROOT / "src", {".py"})
    test_count = count_tests(PROJECT_ROOT / "tests")
    py_lines = count_all_lines(PROJECT_ROOT / "src", {".py"})
    reqs = get_requirements()

    return f"""## 1. Introduction

### 1.1 Project Overview

**ParkSmart** is an enterprise-grade AI-powered parking reservation platform that
combines conversational AI with structured workflow orchestration. The system allows
users to query parking information via natural language and make reservations through
a guided chatbot flow, while administrators review and approve bookings through a
dedicated dashboard.

| Metric | Value |
|--------|-------|
| Backend Source Files | {py_files} |
| Backend Lines of Code | {py_lines:,} |
| Test Cases | {test_count} |
| Dependencies | {len(reqs)} |
| Frontend Framework | Next.js 16 + React 19 |
| AI Orchestration | LangGraph 0.2+ |

### 1.2 Business Problem

Urban parking management faces several challenges:
- **Information fragmentation** — Parking availability, pricing, and hours are scattered
  across static pages that quickly become outdated.
- **Manual reservation processes** — Phone/email bookings are error-prone and unscalable.
- **Lack of intelligent routing** — Users cannot get real-time answers about availability
  or pricing without human intervention.
- **No approval workflow** — Reservation requests lack structured review, leading to
  overbooking and conflicts.

### 1.3 Solution Approach

ParkSmart solves these problems through a multi-layered architecture:

1. **Conversational AI Interface** — Natural language chatbot powered by GPT-4o with
   RAG for accurate, context-aware responses about parking facilities.
2. **Structured Reservation Collection** — State machine guides users through
   step-by-step data collection with validation at each step.
3. **Human-in-the-Loop Approval** — Admin dashboard with LLM-assisted review
   ensures quality control before confirmation.
4. **Real-Time Notifications** — SMTP email service notifies both admins (new requests)
   and users (approval/rejection).
5. **LangGraph Orchestration** — Six-node state graph manages the complete lifecycle
   from user interaction to completion.

### 1.4 Key Objectives

- Provide accurate parking information through semantic search (RAG)
- Automate reservation collection with robust input validation
- Enforce human review before confirming any booking
- Maintain audit trail of all reservations and admin actions
- Support both terminal CLI and web-based interfaces
- Implement enterprise patterns: CI/CD, containerization, IaC

---

"""


# ── Section 2: System Architecture ───────────────────────────────────

def section_architecture() -> str:
    return """## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│                                                                 │
│   ┌─────────────┐    ┌──────────────┐    ┌──────────────┐      │
│   │  Next.js 16  │    │  Admin Panel  │    │  Terminal CLI │      │
│   │  Chat UI     │    │  Dashboard    │    │  Interface    │      │
│   └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
│          │                   │                    │              │
└──────────┼───────────────────┼────────────────────┼──────────────┘
           │  HTTP/REST        │  HTTP/REST         │  Direct
           ▼                   ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                       API GATEWAY                               │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │              FastAPI Server (Port 8000)                  │   │
│   │  /api/chat  │  /api/reservations  │  /api/health        │   │
│   │  /admin/*   │  /api/reservations/{id}/approve|reject    │   │
│   └─────────────────────────┬───────────────────────────────┘   │
│                             │                                   │
└─────────────────────────────┼───────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────┐
│                    ORCHESTRATION LAYER                           │
│                             │                                   │
│   ┌─────────────────────────▼───────────────────────────────┐   │
│   │              LangGraph Pipeline (6 Nodes)                │   │
│   │                                                          │   │
│   │  user_interaction → save_reservation → admin_review      │   │
│   │       → notification → mcp_recording → completion        │   │
│   └───┬──────────┬──────────┬──────────┬──────────┬─────────┘   │
│       │          │          │          │          │              │
│       ▼          ▼          ▼          ▼          ▼              │
│   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐      │
│   │Chatbot │ │SQL     │ │Admin   │ │Email   │ │MCP     │      │
│   │Engine  │ │Store   │ │Agent   │ │Service │ │Client  │      │
│   └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘      │
│       │          │          │          │          │              │
└───────┼──────────┼──────────┼──────────┼──────────┼─────────────┘
        │          │          │          │          │
┌───────┼──────────┼──────────┼──────────┼──────────┼─────────────┐
│       │     DATA & EXTERNAL SERVICES   │          │             │
│       ▼          ▼                     ▼          ▼             │
│  ┌─────────┐ ┌─────────┐        ┌──────────┐ ┌──────────┐     │
│  │Pinecone │ │ SQLite  │        │ SMTP     │ │ MCP      │     │
│  │Vector DB│ │ SQL DB  │        │ Server   │ │ Server   │     │
│  │(Cloud)  │ │(Local)  │        │(External)│ │(:8001)   │     │
│  └─────────┘ └─────────┘        └──────────┘ └──────────┘     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Communication Patterns

| Source | Target | Protocol | Purpose |
|--------|--------|----------|---------|
| Next.js Frontend | FastAPI Backend | REST/JSON over HTTP | Chat messages, reservation CRUD, admin actions |
| FastAPI Server | LangGraph Pipeline | In-process function call | Orchestrate reservation lifecycle |
| Chatbot Engine | Pinecone | HTTPS (gRPC internally) | Vector similarity search for RAG |
| Chatbot Engine | Azure OpenAI | HTTPS | LLM inference (GPT-4o via EPAM DIAL) |
| RAG Chain | SQLite | SQLAlchemy ORM | Dynamic context (hours, prices, availability) |
| Email Service | SMTP Server | SSL/STARTTLS | Notification delivery |
| MCP Client | MCP Server | HTTP REST | Tool invocation for file recording |
| Admin Agent | Azure OpenAI | HTTPS | LLM-assisted reservation review |

### 2.3 Data Flow Summary

**Dual Database Architecture:**
- **Pinecone (Vector DB)** — Stores embeddings of static parking information
  (facility descriptions, policies, FAQ). Used for semantic retrieval in RAG pipeline.
- **SQLite (Relational DB)** — Stores dynamic transactional data: working hours,
  pricing tables, space availability, and reservation records with full lifecycle tracking.

This split ensures that semantic search performance is decoupled from transactional
write throughput, allowing each datastore to be optimized independently.

---

"""


# ── Section 3: Technology Choices ─────────────────────────────────────

def section_technology_choices() -> str:
    return """## 3. Technology Choices

### 3.1 Backend Framework — FastAPI

| Criterion | FastAPI | Flask | Django REST |
|-----------|---------|-------|-------------|
| Async Support | Native (ASGI) | Limited (via gevent) | Partial (Django 4.1+) |
| Auto Docs | Swagger + ReDoc built-in | Manual | DRF Browsable API |
| Type Safety | Pydantic models enforced | None | Serializers |
| Performance | High (Starlette/Uvicorn) | Moderate (WSGI) | Moderate |
| Learning Curve | Low | Very Low | High |

**Decision:** FastAPI provides native async support essential for concurrent LLM calls,
automatic OpenAPI documentation for frontend integration, and Pydantic validation
that catches malformed requests at the boundary.

### 3.2 Frontend Framework — Next.js 16

| Criterion | Next.js | Create React App | Vite + React |
|-----------|---------|-------------------|--------------|
| SSR/SSG | Built-in (App Router) | None | Plugin required |
| Routing | File-based (automatic) | Manual (react-router) | Manual |
| API Routes | Built-in | None | None |
| Production Build | Optimized + CDN-ready | Basic | Fast but manual |
| TypeScript | First-class | Supported | Supported |

**Decision:** Next.js App Router provides file-based routing that maps cleanly to
the `/chat` and `/admin` page structure, plus built-in optimization for production
deployment.

### 3.3 Vector Database — Pinecone

| Criterion | Pinecone | ChromaDB | Weaviate | FAISS |
|-----------|----------|----------|----------|-------|
| Managed Service | Yes (serverless) | Self-hosted | Self-hosted | Library only |
| Scalability | Auto-scaling | Manual | Manual | In-memory |
| Metadata Filtering | Yes | Yes | Yes | No |
| Production Ready | Enterprise-grade | Development | Production | Research |
| Maintenance | Zero-ops | High | High | None (in-process) |

**Decision:** Pinecone's serverless deployment eliminates infrastructure management
while providing sub-100ms similarity search at scale. The managed service aligns with
the project's cloud-first deployment strategy.

### 3.4 AI Orchestration — LangGraph

| Criterion | LangGraph | LangChain Agents | Custom FSM |
|-----------|-----------|------------------|------------|
| State Management | TypedDict (explicit) | AgentState (implicit) | Manual |
| Graph Visualization | Built-in | None | Manual |
| Human-in-Loop | Native interrupt | Custom implementation | Custom |
| Conditional Routing | Declarative edges | Tool-based | if/else chains |
| Reproducibility | Deterministic graph | Non-deterministic | Deterministic |

**Decision:** LangGraph provides declarative state machine semantics that make the
six-node reservation pipeline explicit, testable, and auditable. The conditional
edge system cleanly handles branching between booking and Q&A flows.

### 3.5 Containerization — Docker

**Rationale:**
- Multi-stage builds reduce image size (builder → runtime separation)
- Non-root user execution for security
- Health checks enable orchestration readiness probes
- `docker-compose.yml` defines the complete local development environment
- Environment variable injection isolates secrets from code

### 3.6 CI/CD — GitHub Actions

**Rationale:**
- Native GitHub integration with zero additional infrastructure
- Matrix strategy support for multi-Python-version testing
- Artifact caching (pip, npm) reduces build times by ~60%
- Three parallel workflows: backend tests, frontend validation, Docker build

### 3.7 Infrastructure as Code — Terraform

**Rationale:**
- Declarative infrastructure definition prevents configuration drift
- Render provider enables one-command cloud deployment
- Variable files separate sensitive values from infrastructure logic
- State management provides deployment audit trail

---

"""


# ── Section 4: Folder Structure ──────────────────────────────────────

def section_folder_structure() -> str:
    tree = build_tree(PROJECT_ROOT, max_depth=3)
    return f"""## 4. Folder Structure

### 4.1 Complete Directory Layout

```
{tree}
```

### 4.2 Directory Explanations

| Directory | Purpose | Key Contents |
|-----------|---------|--------------|
| `config/` | Application configuration | `settings.py` — Pydantic BaseSettings reading `.env` |
| `src/` | All backend source code | 7 sub-packages covering every system layer |
| `src/chatbot/` | Conversational AI engine | Chatbot state machine, RAG chain, guardrails |
| `src/database/` | Data persistence | SQLAlchemy ORM (`sql_store.py`), Pinecone wrapper (`vector_store.py`) |
| `src/graph/` | LangGraph orchestration | Pipeline builder, node implementations, state schema |
| `src/agents/` | Admin AI agent | LangChain agent with tools for reservation review |
| `src/api/` | REST API layer | FastAPI server with chat, reservation, and admin endpoints |
| `src/notifications/` | Email service | SMTP with retry, HTML/plain templates, async support |
| `src/mcp/` | Model Context Protocol | Tool server (FastAPI) + client with local fallback |
| `src/data/` | Static knowledge base | `parking_info.txt` + document loader for RAG |
| `src/evaluation/` | RAG quality metrics | Precision@K, Recall@K, answer relevance, latency |
| `src/utils/` | Shared utilities | Email masking, structured logging |
| `tests/` | Test suite (161 tests) | One test file per module, mocked external services |
| `frontend/` | Next.js 16 web application | Chat UI, admin dashboard, Zustand stores |
| `frontend/src/components/` | React components | Chat (3), Admin (5), UI primitives (shadcn) |
| `frontend/src/store/` | State management | Zustand stores: chat, auth, admin, UI |
| `frontend/src/services/` | API integration | Axios-based service layer for backend calls |
| `.github/workflows/` | CI/CD pipelines | Backend CI, Frontend CI, Docker Build validation |
| `terraform/` | Infrastructure as Code | Render deployment with variables and outputs |
| `data/` | Runtime data files | `approved_reservations.txt` (MCP output) |

---

"""


# ── Section 5: File-by-File Explanation ──────────────────────────────

def _file_analysis(rel_path: str, full_path: Path, purpose: str,
                   details: str) -> str:
    """Generate analysis block for a single file."""
    lines = count_lines(full_path) if full_path.exists() else 0

    block = f"#### `{rel_path}`\n\n"
    block += f"**Lines:** {lines} | **Purpose:** {purpose}\n\n"
    block += f"{details}\n\n"

    # Extract Python structure
    if full_path.suffix == ".py" and full_path.exists():
        classes = extract_classes(full_path)
        functions = extract_functions(full_path)
        imports = extract_imports(full_path)

        if classes:
            block += "**Classes:**\n\n"
            for cls in classes:
                doc = f" — {cls['docstring'][:80]}..." if cls['docstring'] else ""
                block += f"- `{cls['name']}`{doc}\n"
                for m in cls['methods'][:12]:
                    prefix = "async " if m['is_async'] else ""
                    args_str = ", ".join(m['args'][:4])
                    block += f"  - `{prefix}{m['name']}({args_str})`\n"
            block += "\n"

        if functions:
            block += "**Functions:**\n\n"
            for fn in functions[:15]:
                prefix = "async " if fn['is_async'] else ""
                args_str = ", ".join(fn['args'][:4])
                doc = f" — {fn['docstring'][:60]}" if fn['docstring'] else ""
                block += f"- `{prefix}{fn['name']}({args_str})`{doc}\n"
            block += "\n"

        if imports:
            key_imports = [i for i in imports if i not in
                           ("os", "re", "sys", "typing", "pathlib", "datetime",
                            "logging", "json", "textwrap", "enum", "dataclasses")]
            if key_imports:
                block += f"**Key Imports:** {', '.join(key_imports[:10])}\n\n"

    return block


def section_file_by_file() -> str:
    S = PROJECT_ROOT / "src"
    sections = "## 5. File-by-File Explanation\n\n"
    sections += (
        "This section provides a detailed analysis of every major file in the project, "
        "explaining its purpose, internal structure, dependencies, and how it integrates "
        "with the rest of the system.\n\n"
    )

    # ── Entry Points ──
    sections += "### 5.1 Entry Points & Configuration\n\n"

    sections += _file_analysis("main.py", PROJECT_ROOT / "main.py",
        "Application entry point supporting multiple execution modes",
        "Serves as the unified launcher for all system components. Supports CLI flags:\n"
        "- `--setup` — Initialize vector DB and SQL DB with parking data\n"
        "- `--evaluate` — Run RAG accuracy and latency benchmarks\n"
        "- `--api` — Start FastAPI REST server on port 8000\n"
        "- `--mcp` — Start MCP tool server on port 8001\n"
        "- `--admin` — Launch admin review CLI\n"
        "- Default — Interactive terminal chatbot\n\n"
        "**Integration:** Instantiates all service objects (chatbot, SQL store, email, MCP client, "
        "admin agent) and passes them to the LangGraph pipeline builder.")

    sections += _file_analysis("config/settings.py", PROJECT_ROOT / "config" / "settings.py",
        "Centralized configuration via Pydantic BaseSettings",
        "Reads all configuration from environment variables (`.env` file). Key settings:\n"
        "- **LLM:** Azure endpoint, API key, model name, temperature\n"
        "- **Embeddings:** Model name (`all-MiniLM-L6-v2`), dimension (384)\n"
        "- **Pinecone:** API key, index name, cloud/region\n"
        "- **SQL:** Database URL (SQLite path)\n"
        "- **SMTP:** Host, port, credentials, admin email\n"
        "- **Guardrails:** Enable/disable toggle, confidence threshold\n\n"
        "**Convention:** All modules import `from config.settings import settings`. "
        "Never use `os.getenv()` directly — Pydantic handles `.env` loading automatically.")

    # ── Chatbot Module ──
    sections += "### 5.2 Chatbot Module (`src/chatbot/`)\n\n"

    sections += _file_analysis("src/chatbot/chatbot.py", S / "chatbot" / "chatbot.py",
        "Main chatbot orchestration with finite state machine",
        "Implements a conversation state machine with states:\n"
        "`IDLE → COLLECTING_NAME → COLLECTING_EMAIL → COLLECTING_CAR → "
        "COLLECTING_SPACE_TYPE → COLLECTING_START → COLLECTING_END → CONFIRMING`\n\n"
        "**Workflow:**\n"
        "1. User message enters `chat()` → guardrails check input\n"
        "2. If in IDLE state → route to RAG for general queries\n"
        "3. If RAG response contains `INTENT:BOOKING` → start reservation flow\n"
        "4. State machine collects fields one-by-one with validation\n"
        "5. On confirmation → save to SQL, notify admin via email\n\n"
        "**Integration:** Uses VectorStore (RAG), SQLStore (save reservation), "
        "EmailService (admin notification), Guardrails (safety filter).")

    sections += _file_analysis("src/chatbot/rag_chain.py", S / "chatbot" / "rag_chain.py",
        "Retrieval-Augmented Generation pipeline (LCEL)",
        "Builds a LangChain Expression Language (LCEL) chain:\n"
        "`retriever → dynamic_context → prompt_template → LLM → output_parser`\n\n"
        "**Features:**\n"
        "- Retrieves top-K documents from Pinecone via cosine similarity\n"
        "- Injects real-time SQL data (hours, prices, availability) as dynamic context\n"
        "- Maintains chat history for multi-turn conversations\n"
        "- System prompt includes `INTENT:BOOKING` detection instruction\n"
        "- Uses AzureChatOpenAI via EPAM DIAL proxy\n\n"
        "**Integration:** Called by `ParkingChatbot._handle_general_query()` for all "
        "non-reservation messages.")

    sections += _file_analysis("src/chatbot/guardrails.py", S / "chatbot" / "guardrails.py",
        "Security layer for PII detection and prompt injection prevention",
        "**Input Protection:**\n"
        "- Regex-based prompt injection detection (ignore instructions, system prompt, etc.)\n"
        "- Data privacy request detection (show all users, dump database)\n"
        "- Returns blocked response with explanation\n\n"
        "**Output Protection:**\n"
        "- Microsoft Presidio NLP engine for PII entity detection\n"
        "- Regex fallback when Presidio/spaCy unavailable\n"
        "- Redacts: email addresses, phone numbers, SSNs, credit cards\n"
        "- Safe patterns list excludes our own contact info from redaction\n"
        "- Configurable confidence threshold (default 0.7)\n\n"
        "**Integration:** Wraps every `chatbot.chat()` call — input checked before "
        "processing, output filtered before returning to user.")

    # ── Database Module ──
    sections += "### 5.3 Database Module (`src/database/`)\n\n"

    sections += _file_analysis("src/database/sql_store.py", S / "database" / "sql_store.py",
        "SQLAlchemy ORM for transactional parking data",
        "**ORM Models (4 tables):**\n"
        "- `WorkingHours` — Day-specific operating hours\n"
        "- `ParkingPrice` — Space type + duration → price mapping\n"
        "- `ParkingAvailability` — Floor × space type → capacity/available\n"
        "- `Reservation` — Full lifecycle (pending → approved/rejected)\n\n"
        "**Key Capabilities:**\n"
        "- Schema migration on startup (`ALTER TABLE` for new columns)\n"
        "- Default data population (hours, prices, 4-floor availability)\n"
        "- Dynamic context generation for RAG injection\n"
        "- StaticPool for in-memory SQLite thread safety\n\n"
        "**Integration:** Used by chatbot (reservation save), admin agent (review/approve), "
        "API server (CRUD endpoints), RAG chain (dynamic context).")

    sections += _file_analysis("src/database/vector_store.py", S / "database" / "vector_store.py",
        "Pinecone vector database wrapper for semantic search",
        "**Capabilities:**\n"
        "- Initializes Pinecone serverless index (384-dim, cosine metric, AWS us-east-1)\n"
        "- Automatic index creation with readiness polling\n"
        "- Batch document upsert with configurable batch size\n"
        "- Similarity search with score (returns documents + cosine distances)\n"
        "- Async variants for all search methods\n"
        "- LangChain retriever interface for LCEL integration\n"
        "- Connection validation and health checks\n"
        "- Retry with exponential backoff via tenacity\n\n"
        "**Integration:** Provides retriever to RAG chain, loaded by `load_data.py` "
        "during setup.")

    # ── Graph Module ──
    sections += "### 5.4 Graph Orchestration Module (`src/graph/`)\n\n"

    sections += _file_analysis("src/graph/state.py", S / "graph" / "state.py",
        "TypedDict schema defining the LangGraph state contract",
        "**GraphState Fields:**\n"
        "- `user_message`, `bot_response` — Current turn I/O\n"
        "- `conversation_phase` — Pipeline phase enum\n"
        "- `reservation_data` — Collected booking information\n"
        "- `reservation_id` — SQL primary key after save\n"
        "- `admin_decision`, `admin_notes` — Review outcome\n"
        "- `notification_sent`, `mcp_recorded` — Completion flags\n"
        "- `history` — Conversation message list\n"
        "- `is_booking_flow`, `needs_admin_input`, `admin_input` — Routing signals\n\n"
        "**PipelinePhase Enum:**\n"
        "`USER_INTERACTION → BOOKING_COMPLETE → AWAITING_ADMIN → ADMIN_REVIEWING → "
        "APPROVED/REJECTED → NOTIFYING → RECORDING → COMPLETED | ERROR`")

    sections += _file_analysis("src/graph/pipeline.py", S / "graph" / "pipeline.py",
        "LangGraph state machine builder and execution engine",
        "**Graph Construction:**\n"
        "1. Creates `StateGraph(GraphState)` with 6 nodes\n"
        "2. Defines conditional edges for routing:\n"
        "   - After user_interaction → save_reservation (if booking) or END (if Q&A)\n"
        "   - After admin_review → notification (if decided) or END (await input)\n"
        "   - After notification → mcp_recording (if approved) or completion (if rejected)\n"
        "3. Compiles to executable graph\n\n"
        "**Execution Functions:**\n"
        "- `run_user_message()` — Process user input through the pipeline\n"
        "- `run_admin_decision()` — Route admin approval through notification→MCP→completion\n\n"
        "**Integration:** Built in `main.py` and `server.py`, receives all service instances.")

    sections += _file_analysis("src/graph/nodes.py", S / "graph" / "nodes.py",
        "Individual node implementations for the LangGraph pipeline",
        "**6 Node Functions:**\n"
        "1. `user_interaction_node()` — Calls chatbot, detects booking completion\n"
        "2. `save_reservation_node()` — Transitions to AWAITING_ADMIN phase\n"
        "3. `admin_review_node()` — Parses admin commands (approve/reject/review)\n"
        "4. `notification_node()` — Updates DB status, sends email notification\n"
        "5. `mcp_recording_node()` — Writes approved reservation to file via MCP\n"
        "6. `completion_node()` — Finalizes the pipeline cycle\n\n"
        "**Singleton Pattern:** Module-level variables hold shared service instances, "
        "initialized once by `initialize_components()` from pipeline builder.")

    # ── Admin Agent ──
    sections += "### 5.5 Admin Agent Module (`src/agents/`)\n\n"

    sections += _file_analysis("src/agents/admin_agent.py", S / "agents" / "admin_agent.py",
        "LangChain agent with tools for intelligent reservation review",
        "**LangChain Tools (3):**\n"
        "- `check_availability` — Query real-time parking availability by space type\n"
        "- `list_pending` — Retrieve all pending reservations\n"
        "- `get_reservation` — Fetch single reservation by ID\n\n"
        "**Agent Capabilities:**\n"
        "- `review_reservation()` — LLM generates recommendation with availability context\n"
        "- `approve_reservation()` — Updates status, emails user, writes MCP file\n"
        "- `reject_reservation()` — Updates status, emails rejection with notes\n"
        "- `get_admin_summary()` — Dashboard metrics (pending/approved/rejected counts)\n\n"
        "**CLI Interface:** `run_admin_cli()` provides terminal commands: "
        "list, all, review, approve, reject, dash, quit.")

    # ── API Server ──
    sections += "### 5.6 API Server Module (`src/api/`)\n\n"

    sections += _file_analysis("src/api/server.py", S / "api" / "server.py",
        "FastAPI REST API for frontend integration and external access",
        "**Endpoint Groups:**\n\n"
        "| Method | Path | Purpose |\n"
        "|--------|------|---------|\n"
        "| GET | `/api/health` | Basic health check |\n"
        "| GET | `/api/health/detailed` | DB + Vector DB + Email status |\n"
        "| POST | `/api/chat` | Send message to chatbot pipeline |\n"
        "| POST | `/api/reservations` | Create new reservation |\n"
        "| GET | `/api/reservations` | List reservations (with status filter) |\n"
        "| GET | `/api/reservations/{id}` | Get reservation by ID |\n"
        "| PUT | `/api/reservations/{id}/approve` | Admin approve |\n"
        "| PUT | `/api/reservations/{id}/reject` | Admin reject |\n\n"
        "**Middleware:** CORS configured for `localhost:3000` (frontend dev server)\n\n"
        "**Note:** `_pipeline_state` is global mutable state — single-session demo only, "
        "not thread-safe for concurrent requests.")

    # ── Notifications ──
    sections += "### 5.7 Notification Module (`src/notifications/`)\n\n"

    sections += _file_analysis("src/notifications/email_service.py",
        S / "notifications" / "email_service.py",
        "SMTP email service with retry, templates, and console fallback",
        "**Capabilities:**\n"
        "- SSL (port 465) and STARTTLS (port 587) support\n"
        "- Exponential backoff retry (3 attempts via tenacity)\n"
        "- HTML + plain text email templates\n"
        "- Async wrappers for non-blocking sends\n"
        "- Console fallback when SMTP is unconfigured\n"
        "- Email masking in console output for privacy\n\n"
        "**Email Types:**\n"
        "1. Admin notification — New reservation alert\n"
        "2. User approval — Confirmation with parking instructions\n"
        "3. User rejection — Explanation with admin notes\n\n"
        "**Integration:** Called by notification_node (LangGraph), admin_agent, "
        "and API server approve/reject endpoints.")

    # ── MCP Module ──
    sections += "### 5.8 MCP Module (`src/mcp/`)\n\n"

    sections += _file_analysis("src/mcp/mcp_server.py", S / "mcp" / "mcp_server.py",
        "FastAPI-based MCP tool server implementing tool discovery and execution",
        "**MCP Protocol Endpoints:**\n"
        "- `GET /mcp/health` — Server health (no auth)\n"
        "- `POST /mcp/tools/list` — Discover available tools (API key required)\n"
        "- `POST /mcp/tools/call` — Execute a tool by name (API key required)\n\n"
        "**Registered Tools:**\n"
        "1. `write_reservation_to_file` — Append approved reservation to text file\n"
        "2. `read_approved_reservations` — Read recorded reservations\n\n"
        "**Security:** API key authentication via `X-MCP-API-KEY` header.")

    sections += _file_analysis("src/mcp/mcp_client.py", S / "mcp" / "mcp_client.py",
        "HTTP client for invoking MCP server tools with local fallback",
        "**Features:**\n"
        "- Server availability check before each call\n"
        "- Automatic fallback to local file write when server is down\n"
        "- API key authentication in request headers\n"
        "- Configurable timeout for HTTP requests\n\n"
        "**Integration:** Called by `mcp_recording_node()` in LangGraph pipeline and "
        "`admin_agent.approve_reservation()` method.")

    # ── Data & Evaluation ──
    sections += "### 5.9 Data & Evaluation Modules\n\n"

    sections += _file_analysis("src/data/load_data.py", S / "data" / "load_data.py",
        "Document loading and chunking for vector store ingestion",
        "**Functions:**\n"
        "- `load_and_split_documents()` — Load `parking_info.txt`, split into 500-char "
        "chunks with 50-char overlap using `RecursiveCharacterTextSplitter`\n"
        "- `get_sample_questions()` — 10 test questions for evaluation\n"
        "- `get_ground_truth_answers()` — Expected answers for accuracy measurement")

    sections += _file_analysis("src/evaluation/evaluator.py", S / "evaluation" / "evaluator.py",
        "RAG pipeline quality and performance evaluation",
        "**Metrics Computed:**\n"
        "- Retrieval time (ms) — Vector search latency\n"
        "- Generation time (ms) — LLM inference latency\n"
        "- Precision@K — Fraction of retrieved docs relevant to answer\n"
        "- Recall@K — Fraction of relevant info retrieved\n"
        "- Answer relevance — Jaccard similarity between generated and expected\n\n"
        "**Output:** `EvaluationReport` with per-question results and aggregated statistics.")

    # ── Utilities ──
    sections += "### 5.10 Utility Modules\n\n"

    sections += _file_analysis("src/utils/masking.py", S / "utils" / "masking.py",
        "Email masking utility for privacy-safe display",
        "**Functions:**\n"
        "- `mask_email(email)` → `sa****@gmail.com` format (shows first 2 chars)\n"
        "- `validate_email(email)` → Regex validation\n\n"
        "**Convention:** All user-facing email display must use `mask_email()`. "
        "Guardrails safe_patterns list includes masked email regex to prevent "
        "Presidio from re-redacting already-masked addresses.")

    sections += "---\n\n"
    return sections


# ── Section 6: RAG Workflow ──────────────────────────────────────────

def section_rag_workflow() -> str:
    return """## 6. RAG Workflow

### 6.1 Overview

The Retrieval-Augmented Generation (RAG) pipeline combines semantic search over
static parking knowledge with real-time SQL data injection to produce accurate,
context-aware responses.

### 6.2 Pipeline Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  User Query  │────▶│  HuggingFace     │────▶│  Pinecone       │
│              │     │  Embeddings      │     │  Vector Search   │
│              │     │  (MiniLM-L6-v2)  │     │  (cosine, top-4) │
└─────────────┘     └──────────────────┘     └────────┬────────┘
                                                       │
                    ┌──────────────────┐               │
                    │  SQLite Dynamic   │               │
                    │  Context          │               │
                    │  (hours, prices,  │               │
                    │   availability)   │──────┐        │
                    └──────────────────┘      │        │
                                              ▼        ▼
                                     ┌─────────────────────┐
                                     │  Prompt Template     │
                                     │  (system + context   │
                                     │   + history + query) │
                                     └──────────┬──────────┘
                                                │
                                                ▼
                                     ┌─────────────────────┐
                                     │  GPT-4o (Azure)      │
                                     │  via EPAM DIAL       │
                                     └──────────┬──────────┘
                                                │
                                                ▼
                                     ┌─────────────────────┐
                                     │  Output Parser       │
                                     │  + Guardrails Filter │
                                     └─────────────────────┘
```

### 6.3 Embedding Strategy

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Model | `all-MiniLM-L6-v2` | Best balance of speed and quality for sentence embeddings |
| Dimension | 384 | Sufficient for domain-specific parking vocabulary |
| Metric | Cosine similarity | Normalized comparison regardless of vector magnitude |
| Top-K | 4 | Enough context without exceeding prompt token limits |

### 6.4 Document Processing

1. **Source:** `src/data/parking_info.txt` — Static parking facility information
2. **Chunking:** `RecursiveCharacterTextSplitter` with 500-char chunks, 50-char overlap
3. **Storage:** Embedded chunks upserted to Pinecone serverless index
4. **Retrieval:** Query embedded → cosine search → top-4 chunks returned

### 6.5 Dynamic Context Injection

In addition to retrieved documents, the RAG chain injects real-time data from SQLite:
- **Working Hours** — Current operating schedule per day
- **Pricing** — Space type × duration pricing table
- **Availability** — Floor-by-floor space counts (total vs. available)

This dual-source approach ensures responses reflect both static policies and
current operational state.

### 6.6 Intent Detection

The system prompt instructs the LLM to include `INTENT:BOOKING` in responses when
the user expresses intent to make a reservation. The chatbot detects this marker
and transitions from RAG Q&A mode to the reservation collection state machine.

---

"""


# ── Section 7: LangGraph Workflow ────────────────────────────────────

def section_langgraph_workflow() -> str:
    return """## 7. LangGraph Workflow

### 7.1 State Machine Design

The LangGraph pipeline implements a 6-node directed acyclic graph with conditional
edges that route execution based on conversation state.

### 7.2 Node Descriptions

| Node | Input State | Processing | Output State |
|------|-------------|------------|--------------|
| `user_interaction` | User message | Chatbot processes query or reservation step | Bot response + booking detection |
| `save_reservation` | Completed booking data | Persist to SQL with 'pending' status | Reservation ID + AWAITING_ADMIN |
| `admin_review` | Admin command | Parse approve/reject/review, generate summary | Decision + admin notes |
| `notification` | Admin decision | Update DB status, send email to user | notification_sent = True |
| `mcp_recording` | Approved reservation | Write to file via MCP server/local fallback | mcp_recorded = True |
| `completion` | All flags set | Finalize cycle, log outcome | COMPLETED phase |

### 7.3 Conditional Edge Logic

```
                    ┌────────────────────┐
                    │  user_interaction   │
                    └────────┬───────────┘
                             │
                    ┌────────▼───────────┐
                    │  is_booking_flow?   │
                    └────────┬───────────┘
                        Yes/ │ \\No
                       /     │   \\
            ┌─────────▼──┐   │   ┌▼────┐
            │save_        │   │   │ END │
            │reservation  │   │   └─────┘
            └──────┬──────┘   │
                   │          │
            ┌──────▼──────┐   │
            │admin_review  │   │
            └──────┬──────┘   │
                   │          │
          ┌────────▼────────┐ │
          │decision made?   │ │
          └────────┬────────┘ │
              Yes/ │ \\No      │
             /     │   \\      │
     ┌──────▼───┐  │  ┌▼────┐│
     │notification│  │  │END ││ (await admin input)
     └──────┬───┘  │  └─────┘│
            │      │          │
     ┌──────▼─────────┐      │
     │  approved?      │      │
     └──────┬─────────┘      │
        Yes/ │ \\No            │
       /     │   \\            │
┌─────▼────┐ │  ┌▼──────────┐│
│mcp_       │ │  │completion  ││
│recording  │ │  └───────────┘│
└──────┬───┘ │                │
       │     │                │
┌──────▼────┐│                │
│completion  ││                │
└───────────┘│                │
```

### 7.4 Human-in-the-Loop Design

The pipeline implements human-in-the-loop by **interrupting the graph** at the
`admin_review` node:

1. User completes reservation → pipeline runs through `save_reservation`
2. `admin_review` returns `needs_admin_input=True` → graph yields END
3. System waits for external admin action (CLI or API endpoint)
4. Admin decision triggers `run_admin_decision()` → resumes from `admin_review`
5. Pipeline continues through notification → MCP → completion

This design avoids polling loops and integrates cleanly with both the CLI
and REST API admin interfaces.

### 7.5 State Persistence

`GraphState` is a TypedDict passed through all nodes. Each node returns only
the fields it modifies, and LangGraph merges updates automatically. The state
includes:
- Conversation context (message, response, history)
- Reservation lifecycle (data, ID, status)
- Admin decision chain (decision, notes)
- Completion flags (notification_sent, mcp_recorded)
- Error tracking (error field)

---

"""


# ── Section 8: Reservation Workflow ──────────────────────────────────

def section_reservation_workflow() -> str:
    return """## 8. Reservation Workflow

### 8.1 End-to-End Lifecycle

```
┌──────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   User    │──▶│   Chatbot    │──▶│   SQL Store   │──▶│   Email      │
│  Request  │   │   Collects   │   │   Saves as    │   │   Notifies   │
│           │   │   6 Fields   │   │   'pending'   │   │   Admin      │
└──────────┘   └──────────────┘   └──────────────┘   └──────┬───────┘
                                                             │
                                                             ▼
┌──────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   User    │◀──│   Email      │◀──│   DB Update   │◀──│   Admin      │
│  Notified │   │   Sends      │   │   approved/   │   │   Reviews    │
│           │   │   Result     │   │   rejected    │   │   Decides    │
└──────────┘   └──────────────┘   └──────────────┘   └──────────────┘
                                                             │
                                                      (if approved)
                                                             │
                                                             ▼
                                                      ┌──────────────┐
                                                      │   MCP Server  │
                                                      │   Records to  │
                                                      │   File        │
                                                      └──────────────┘
```

### 8.2 Data Collection State Machine

The chatbot collects reservation data through a strict sequence of states:

| Step | State | Collected Field | Validation |
|------|-------|-----------------|------------|
| 1 | COLLECTING_NAME | First name, last name | Non-empty strings |
| 2 | COLLECTING_EMAIL | Email address | Regex pattern match |
| 3 | COLLECTING_CAR | Car/license number | Non-empty string |
| 4 | COLLECTING_SPACE_TYPE | Parking space type | One of: standard, large, ev, vip, disabled |
| 5 | COLLECTING_START | Start date/time | Valid datetime, within operating hours |
| 6 | COLLECTING_END | End date/time | After start time, within operating hours |
| 7 | CONFIRMING | User confirmation | Yes/No response |

### 8.3 Admin Review Process

Administrators can review reservations through two interfaces:

**CLI Interface (`run_admin_cli`):**
- `list` — Show pending reservations
- `review <id>` — Get LLM-generated recommendation with availability data
- `approve <id> [notes]` — Approve with optional notes
- `reject <id> [notes]` — Reject with reason

**REST API (Admin Dashboard):**
- `PUT /api/reservations/{id}/approve` — Approve via API
- `PUT /api/reservations/{id}/reject` — Reject via API

### 8.4 Notification Templates

Each notification includes both HTML and plain text variants:

| Event | Recipient | Content |
|-------|-----------|---------|
| New reservation | Admin | Reservation details, review prompt |
| Approval | User | Confirmation, parking instructions, space details |
| Rejection | User | Reason for rejection, admin notes, rebooking suggestion |

---

"""


# ── Section 9: Frontend Architecture ─────────────────────────────────

def section_frontend() -> str:
    return """## 9. Frontend Architecture

### 9.1 Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Next.js | 16.x | React framework with App Router |
| React | 19.x | UI component library |
| TypeScript | 5.x | Type safety |
| Tailwind CSS | 4.x | Utility-first styling |
| Zustand | 5.x | Lightweight state management |
| shadcn/ui | Latest | Pre-built accessible components |
| Axios | Latest | HTTP client for API calls |
| Framer Motion | Latest | Animations and transitions |
| Lucide React | Latest | Icon library |
| Sonner | Latest | Toast notifications |

### 9.2 Component Hierarchy

```
app/
├── layout.tsx              # Root layout + ThemeProvider
├── page.tsx                # Landing page with navigation
├── chat/
│   └── page.tsx            # Chat interface page
└── admin/
    └── page.tsx            # Admin dashboard page

components/
├── chat/
│   ├── ChatMessage.tsx     # Individual message bubble (user/bot)
│   ├── ChatInput.tsx       # Message input with send button
│   └── ChatSidebar.tsx     # Conversation history panel
├── admin/
│   ├── AdminLoginGate.tsx  # Authentication gate component
│   ├── ReservationTable.tsx# Sortable/filterable reservation table
│   ├── ReservationModal.tsx# Approve/reject modal with notes
│   ├── StatsCards.tsx      # Dashboard metric cards
│   └── ActivityFeed.tsx    # Recent actions timeline
└── ui/                     # shadcn/ui primitives (button, card, etc.)
```

### 9.3 State Management (Zustand)

| Store | File | State | Purpose |
|-------|------|-------|---------|
| `chatStore` | `store/chatStore.ts` | Messages, loading, error | Chat conversation state |
| `authStore` | `store/authStore.ts` | User, isAuthenticated | Admin authentication |
| `adminStore` | `store/adminStore.ts` | Reservations, filters, selected | Admin dashboard data |
| `uiStore` | `store/uiStore.ts` | Theme, sidebar toggle | UI preferences |

### 9.4 API Integration Layer

```
services/
├── chatService.ts          # POST /api/chat — Send/receive messages
├── reservationService.ts   # CRUD operations on /api/reservations
└── adminService.ts         # Admin-specific endpoints

lib/
└── api.ts                  # Axios instance with baseURL + error interceptor
```

**Base URL:** Configured via `NEXT_PUBLIC_API_URL` environment variable
(defaults to `http://localhost:8000`).

### 9.5 Authentication Flow

The admin dashboard uses a simple credentials gate:
1. `AdminLoginGate` component checks `authStore.isAuthenticated`
2. If not authenticated, displays login form
3. On valid credentials (demo: `admin` / `1234`), sets auth state
4. All admin API calls proceed with authenticated context

---

"""


# ── Section 10: Backend Architecture ─────────────────────────────────

def section_backend() -> str:
    return """## 10. Backend Architecture

### 10.1 Application Structure

```
FastAPI Application (server.py)
│
├── Startup Events
│   ├── Initialize SQLStore (SQLAlchemy → SQLite)
│   ├── Initialize EmailService (SMTP connection)
│   └── Lazy-init LangGraph Pipeline (on first /api/chat call)
│
├── Middleware
│   └── CORS (origins: localhost:3000)
│
├── Route Groups
│   ├── /api/health      — Health checks (basic + detailed)
│   ├── /api/chat        — Chatbot pipeline interaction
│   ├── /api/reservations — CRUD + admin actions
│   └── /admin/*         — Legacy admin endpoints
│
└── Dependencies
    ├── sql_store        — Shared SQLStore instance
    ├── email_service    — Shared EmailService instance
    └── _pipeline_state  — Global mutable pipeline state
```

### 10.2 Request Processing Flow

```
HTTP Request
    │
    ▼
┌─────────────┐
│  CORS Check  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Pydantic    │
│  Validation  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Route       │
│  Handler     │
└──────┬──────┘
       │
       ├──▶ SQLStore (DB operations)
       ├──▶ Pipeline (chatbot + LangGraph)
       ├──▶ EmailService (notifications)
       └──▶ MCP Client (file recording)
       │
       ▼
┌─────────────┐
│  JSON        │
│  Response    │
└─────────────┘
```

### 10.3 Service Layer Design

| Service | Lifecycle | Thread Safety | Initialization |
|---------|-----------|---------------|----------------|
| `SQLStore` | Singleton | Session-per-request | App startup |
| `EmailService` | Singleton | Stateless methods | App startup |
| `LangGraph Pipeline` | Singleton | NOT thread-safe | Lazy (first chat) |
| `MCP Client` | Per-call | Stateless | Within pipeline |
| `Admin Agent` | Per-pipeline | Stateless methods | Pipeline creation |

### 10.4 Error Handling Strategy

- **HTTP 400** — Invalid request body (Pydantic validation failure)
- **HTTP 404** — Reservation not found
- **HTTP 409** — Reservation already processed (approve/reject conflict)
- **HTTP 500** — Unhandled exceptions wrapped in `StatusResponse`
- **Custom Exceptions:** `VectorStoreError`, `EmailServiceError` with structured error data
- **Retry Logic:** Exponential backoff via `tenacity` for Pinecone and SMTP calls

---

"""


# ── Section 11: CI/CD Pipeline ───────────────────────────────────────

def section_cicd() -> str:
    return """## 11. CI/CD Pipeline

### 11.1 Workflow Architecture

```
GitHub Push (main branch)
         │
         ├──────────────────────┬──────────────────────┐
         ▼                      ▼                      ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  Backend CI       │  │  Frontend CI      │  │  Docker Build     │
│  (.yml)           │  │  (.yml)           │  │  (.yml)           │
│                   │  │                   │  │                   │
│  ┌─────────────┐  │  │  ┌─────────────┐  │  │  ┌─────────────┐  │
│  │ Lint (flake8)│  │  │  │ Lint (ESLint│  │  │  │ Build Backend│  │
│  │ + mypy      │  │  │  │ + TypeScript│  │  │  │ Dockerfile   │  │
│  └──────┬──────┘  │  │  └──────┬──────┘  │  │  └──────┬──────┘  │
│         │         │  │         │         │  │         │         │
│  ┌──────▼──────┐  │  │  ┌──────▼──────┐  │  │  ┌──────▼──────┐  │
│  │ Test Suite  │  │  │  │ Production  │  │  │  │ Build Front  │  │
│  │ (pytest +   │  │  │  │ Build Test  │  │  │  │ Dockerfile   │  │
│  │  coverage)  │  │  │  └─────────────┘  │  │  └──────┬──────┘  │
│  └──────┬──────┘  │  │                   │  │         │         │
│         │         │  │                   │  │  ┌──────▼──────┐  │
│  ┌──────▼──────┐  │  │                   │  │  │ Validate    │  │
│  │ Validate    │  │  │                   │  │  │ Compose     │  │
│  │ FastAPI     │  │  │                   │  │  └──────┬──────┘  │
│  │ Import      │  │  │                   │  │         │         │
│  └─────────────┘  │  │                   │  │  ┌──────▼──────┐  │
│                   │  │                   │  │  │ Validate    │  │
│                   │  │                   │  │  │ Terraform   │  │
│                   │  │                   │  │  └─────────────┘  │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

### 11.2 Backend CI Workflow

| Job | Steps | Purpose |
|-----|-------|---------|
| **Lint** | Install deps → flake8 → mypy | Code style + type checking |
| **Test Suite** | Install deps + spaCy → pytest --cov | Run 161 tests with coverage |
| **Validate FastAPI** | Import `src.api.server:app` | Verify server can start |

**Environment:** Python 3.11, pip cache, mock API keys via GitHub Secrets.

### 11.3 Frontend CI Workflow

| Job | Steps | Purpose |
|-----|-------|---------|
| **Lint & TypeScript** | npm ci → ESLint → tsc --noEmit | Code quality + type safety |
| **Production Build** | npm run build | Verify Next.js production bundle compiles |

**Environment:** Node.js 20, npm cache.

### 11.4 Docker Build Workflow

| Job | Steps | Purpose |
|-----|-------|---------|
| **Build Backend** | docker build -f Dockerfile | Verify backend image builds |
| **Build Frontend** | docker build -f frontend/Dockerfile | Verify frontend image builds |
| **Validate Compose** | docker compose config | Verify compose file syntax |
| **Validate Terraform** | terraform init + validate + fmt | IaC validation |

---

"""


# ── Section 12: Docker & Deployment ──────────────────────────────────

def section_docker() -> str:
    return """## 12. Docker & Deployment

### 12.1 Backend Dockerfile (Multi-Stage)

```
Stage 1: Builder
├── Base: python:3.11-slim
├── Install: system deps (gcc, build-essential)
├── Create: virtualenv in /opt/venv
├── Install: Python dependencies from requirements.txt
└── Download: spaCy en_core_web_lg model

Stage 2: Runtime
├── Base: python:3.11-slim
├── Copy: /opt/venv from builder
├── Copy: application source code
├── Create: non-root user (appuser:appgroup)
├── Expose: port 8000
├── Healthcheck: GET /api/health every 30s
└── CMD: uvicorn src.api.server:app --host 0.0.0.0 --port 8000
```

### 12.2 Docker Compose Architecture

```yaml
services:
  backend:
    build: .
    ports: 8000:8000
    env_file: .env
    volumes:
      - backend-data:/app/data
      - backend-logs:/app/logs
    healthcheck: /api/health

  frontend:
    build: ./frontend
    ports: 3000:3000
    depends_on:
      backend:
        condition: service_healthy
    environment:
      NEXT_PUBLIC_API_URL: http://backend:8000
```

### 12.3 Environment Variables

| Variable | Service | Purpose | Secret |
|----------|---------|---------|--------|
| `DIAL_API_KEY` | Backend | Azure OpenAI access | Yes |
| `PINECONE_API_KEY` | Backend | Vector DB access | Yes |
| `SMTP_HOST` | Backend | Email server | No |
| `SMTP_PORT` | Backend | Email port | No |
| `SMTP_USERNAME` | Backend | Email auth | Yes |
| `SMTP_PASSWORD` | Backend | Email auth | Yes |
| `ADMIN_EMAIL` | Backend | Notification recipient | No |
| `SQL_DATABASE_URL` | Backend | Database path | No |
| `NEXT_PUBLIC_API_URL` | Frontend | API base URL | No |

### 12.4 Deployment Architecture

```
┌──────────────────────────────────────────┐
│           Production Environment          │
│                                          │
│  ┌────────────────┐  ┌────────────────┐  │
│  │   Backend       │  │   Frontend     │  │
│  │   Container     │  │   Container    │  │
│  │   :8000         │──│   :3000        │  │
│  │   (Uvicorn)     │  │   (Next.js)    │  │
│  └────────┬───────┘  └────────────────┘  │
│           │                              │
│  ┌────────▼───────┐                      │
│  │   Data Volume   │                      │
│  │   /app/data     │                      │
│  │   /app/logs     │                      │
│  └────────────────┘                      │
│                                          │
└──────────────────────────────────────────┘
         │              │
         ▼              ▼
    ┌─────────┐   ┌──────────┐
    │Pinecone │   │ SMTP     │
    │(Cloud)  │   │ Server   │
    └─────────┘   └──────────┘
```

---

"""


# ── Section 13: Terraform ────────────────────────────────────────────

def section_terraform() -> str:
    return """## 13. Terraform

### 13.1 Infrastructure as Code Overview

The project includes Terraform configurations for deploying the backend to
Render's cloud platform.

### 13.2 File Structure

| File | Purpose |
|------|---------|
| `terraform/provider.tf` | Render provider configuration |
| `terraform/main.tf` | Web service resource definition |
| `terraform/variables.tf` | Input variables (API keys, settings) |
| `terraform/outputs.tf` | Deployment URL output |

### 13.3 Resource Definition

```hcl
resource "render_web_service" "parksmart_backend" {
  name       = var.backend_name        # "parksmart-backend"
  region     = var.backend_region      # "oregon"
  plan       = var.backend_plan        # "free"
  runtime    = "python"

  start_command = "uvicorn src.api.server:app --host 0.0.0.0 --port $PORT"

  env_vars = {
    DIAL_API_KEY    = var.dial_api_key
    PINECONE_API_KEY = var.pinecone_api_key
    SMTP_HOST       = var.smtp_host
    SMTP_PORT       = var.smtp_port
    SMTP_USERNAME   = var.smtp_username
    SMTP_PASSWORD   = var.smtp_password
    ADMIN_EMAIL     = var.admin_email
    PYTHON_VERSION  = var.python_version
  }
}
```

### 13.4 Variable Definitions

| Variable | Type | Default | Sensitive |
|----------|------|---------|-----------|
| `render_api_key` | string | — | Yes |
| `backend_name` | string | parksmart-backend | No |
| `backend_region` | string | oregon | No |
| `backend_plan` | string | free | No |
| `dial_api_key` | string | — | Yes |
| `pinecone_api_key` | string | — | Yes |
| `smtp_host` | string | — | No |
| `smtp_port` | string | 587 | No |
| `smtp_username` | string | — | Yes |
| `smtp_password` | string | — | Yes |
| `admin_email` | string | — | No |
| `python_version` | string | 3.11.0 | No |

### 13.5 Deployment Workflow

```
terraform init          # Download Render provider
terraform plan          # Preview infrastructure changes
terraform apply         # Deploy backend service
terraform output url    # Get deployed service URL
```

---

"""


# ── Section 14: Security ─────────────────────────────────────────────

def section_security() -> str:
    return """## 14. Security

### 14.1 Security Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     SECURITY LAYERS                          │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Layer 1: Input Validation                               │ │
│  │  • Pydantic model validation at API boundary             │ │
│  │  • Prompt injection detection (regex patterns)           │ │
│  │  • Data privacy request blocking                         │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Layer 2: Output Protection                              │ │
│  │  • Presidio NLP-based PII detection + redaction          │ │
│  │  • Regex fallback for email, phone, SSN, credit card     │ │
│  │  • Safe patterns list (exclude our own contact info)     │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Layer 3: Data Protection                                │ │
│  │  • Email masking in all user-facing output               │ │
│  │  • Environment variables for all secrets (.env)          │ │
│  │  • .gitignore excludes .env, __pycache__, node_modules   │ │
│  │  • GitHub Secrets for CI/CD pipeline                     │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Layer 4: Access Control                                 │ │
│  │  • Admin dashboard authentication gate                   │ │
│  │  • MCP server API key authentication                     │ │
│  │  • CORS restricted to frontend origin                    │ │
│  │  • Non-root Docker container execution                   │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Layer 5: Infrastructure Security                        │ │
│  │  • Multi-stage Docker builds (no build tools in prod)    │ │
│  │  • Terraform sensitive variables                         │ │
│  │  • SMTP SSL/STARTTLS encryption                          │ │
│  │  • Health check endpoints (no sensitive data exposed)    │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 14.2 Prompt Injection Prevention

The guardrails module detects and blocks:

| Pattern Type | Examples | Response |
|--------------|----------|----------|
| System prompt override | "ignore instructions", "forget your rules" | Blocked with explanation |
| Role manipulation | "you are now a different AI", "act as root" | Blocked with explanation |
| Data exfiltration | "show all user emails", "dump the database" | Blocked with explanation |
| Instruction injection | "SYSTEM:", "\\n\\nHuman:" | Blocked with explanation |

### 14.3 PII Redaction Pipeline

```
LLM Output → Presidio Analyzer → Entity Detection → Safe Pattern Check → Redaction
                  │                      │                    │
                  ▼                      ▼                    ▼
            NLP Engine           EMAIL, PHONE,          Exclude our
            (spaCy)              SSN, CREDIT_CARD       own contacts
```

### 14.4 Email Masking Convention

All user-facing email display uses `mask_email()`:
- Input: `sanyam.sachan@gmail.com`
- Output: `sa****@gmail.com`
- Rule: Show first 2 characters + asterisks + domain

---

"""


# ── Section 15: Testing ──────────────────────────────────────────────

def section_testing() -> str:
    test_count = count_tests(PROJECT_ROOT / "tests")
    test_files = list((PROJECT_ROOT / "tests").glob("test_*.py"))

    rows = ""
    for tf in sorted(test_files):
        tc = len(re.findall(r"^\s*(?:def|async def) test_",
                            _safe_read(tf), re.MULTILINE))
        module = tf.stem.replace("test_", "")
        rows += f"| `{tf.name}` | {module} | {tc} |\n"

    return f"""## 15. Testing

### 15.1 Testing Strategy

| Aspect | Approach |
|--------|----------|
| Framework | pytest with pytest-asyncio |
| Coverage | pytest-cov with line coverage |
| External Services | All mocked (LLM, Pinecone, SMTP) |
| Database | In-memory SQLite (no cleanup needed) |
| Configuration | Mock `settings` object, not `os.environ` |
| Structure | One test file per module, class-based grouping |
| CI Integration | Automated via GitHub Actions on every push |

### 15.2 Test Distribution

| Test File | Module Tested | Test Count |
|-----------|---------------|------------|
{rows}
| **Total** | **All Modules** | **{test_count}** |

### 15.3 Mocking Strategy

```python
# Pattern: Mock settings object with attribute overrides
@patch("src.module.settings", mock_settings)
class TestModule:
    def setup_method(self):
        self.mock_settings = MagicMock()
        self.mock_settings.attribute = "test_value"

# Pattern: Mock external LLM calls
@patch("src.chatbot.rag_chain.AzureChatOpenAI")
def test_rag_query(self, mock_llm):
    mock_llm.return_value.invoke.return_value = "mocked response"

# Pattern: In-memory SQLite
sql_store = SQLStore("sqlite:///:memory:")
sql_store.initialize_default_data()
```

### 15.4 Test Categories

| Category | Purpose | Examples |
|----------|---------|---------|
| Unit Tests | Test individual functions/methods | Email masking, PII detection |
| Integration Tests | Test module interactions | Chatbot + SQL store, API + pipeline |
| Validation Tests | Verify constraints | State transitions, input validation |
| Error Path Tests | Test failure handling | Connection errors, invalid data |

### 15.5 Running Tests

```bash
# Run all tests
python -m pytest

# Run with verbose output
python -m pytest -v

# Run with coverage
python -m pytest --cov=src --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_chatbot.py

# Run specific test class
python -m pytest tests/test_chatbot.py::TestParkingChatbot
```

---

"""


# ── Section 16: Future Enhancements ──────────────────────────────────

def section_future_enhancements() -> str:
    return """## 16. Future Enhancements

### 16.1 Short-Term Improvements

| Enhancement | Technology | Impact |
|-------------|------------|--------|
| **Session-based state** | Redis | Thread-safe concurrent users, session persistence |
| **JWT Authentication** | PyJWT + OAuth2 | Proper admin auth replacing demo credentials |
| **WebSocket Chat** | FastAPI WebSocket | Real-time bidirectional messaging |
| **Rate Limiting** | slowapi / Redis | API abuse prevention |
| **Structured Logging** | structlog + ELK | Centralized log aggregation and search |

### 16.2 Medium-Term Features

| Enhancement | Technology | Impact |
|-------------|------------|--------|
| **Payment Gateway** | Stripe API | Collect parking fees at reservation time |
| **AI Parking Prediction** | scikit-learn / Prophet | Predict availability based on historical data |
| **Multi-Language Support** | i18n + LLM translation | Serve international users |
| **Mobile App** | React Native / Expo | Native mobile experience |
| **Webhook Notifications** | FastAPI + httpx | Slack/Teams integration for admin alerts |

### 16.3 Long-Term Architecture

| Enhancement | Technology | Impact |
|-------------|------------|--------|
| **Kubernetes Deployment** | K8s + Helm | Auto-scaling, rolling updates, self-healing |
| **Message Queue** | RabbitMQ / Kafka | Decouple notification and MCP recording |
| **Database Migration** | PostgreSQL + Alembic | Production-grade relational DB with schema versioning |
| **API Gateway** | Kong / AWS API Gateway | Centralized rate limiting, auth, and monitoring |
| **Observability** | Prometheus + Grafana | Metrics, dashboards, and alerting |
| **A/B Testing** | LaunchDarkly | Feature flags for gradual rollouts |

### 16.4 Scaling Strategy

```
Current (Monolith)              Target (Microservices)
┌──────────────┐                ┌──────────────┐
│  FastAPI      │                │  API Gateway  │
│  (all-in-one) │                └──────┬───────┘
└──────────────┘                       │
                                ┌──────┼───────┐
                                ▼      ▼       ▼
                           ┌────────┐ ┌─────┐ ┌──────┐
                           │Chat    │ │Admin│ │Notify│
                           │Service │ │Svc  │ │Svc   │
                           └────────┘ └─────┘ └──────┘
                                │      │       │
                                ▼      ▼       ▼
                           ┌────────────────────────┐
                           │    Message Queue        │
                           │    (RabbitMQ/Kafka)     │
                           └────────────────────────┘
```

---

"""


# ── Appendix: Code Metrics ────────────────────────────────────────────

def section_code_metrics() -> str:
    py_src = count_all_lines(PROJECT_ROOT / "src", {".py"})
    py_test = count_all_lines(PROJECT_ROOT / "tests", {".py"})
    py_config = count_all_lines(PROJECT_ROOT / "config", {".py"})
    reqs = get_requirements()
    test_count = count_tests(PROJECT_ROOT / "tests")

    # Frontend lines
    fe_dir = PROJECT_ROOT / "frontend" / "src"
    ts_lines = count_all_lines(fe_dir, {".ts", ".tsx"}) if fe_dir.exists() else 0
    css_lines = count_all_lines(fe_dir, {".css"}) if fe_dir.exists() else 0

    src_files = count_files(PROJECT_ROOT / "src", {".py"})
    test_files = count_files(PROJECT_ROOT / "tests", {".py"})
    fe_files = count_files(fe_dir, {".ts", ".tsx"}) if fe_dir.exists() else 0

    return f"""## Appendix A: Code Metrics

### A.1 Lines of Code Summary

| Category | Files | Lines |
|----------|-------|-------|
| Backend Source (`src/`) | {src_files} | {py_src:,} |
| Tests (`tests/`) | {test_files} | {py_test:,} |
| Configuration (`config/`) | — | {py_config:,} |
| Frontend TypeScript (`frontend/src/`) | {fe_files} | {ts_lines:,} |
| Frontend CSS | — | {css_lines:,} |
| **Total** | **{src_files + test_files + fe_files}** | **{py_src + py_test + py_config + ts_lines + css_lines:,}** |

### A.2 Dependency Count

| Category | Count |
|----------|-------|
| Python packages | {len(reqs)} |
| Test cases | {test_count} |

### A.3 Architecture Component Count

| Component | Count |
|-----------|-------|
| LangGraph Nodes | 6 |
| API Endpoints | 10+ |
| SQLAlchemy Models | 4 |
| Zustand Stores | 4 |
| React Components | 8+ |
| CI/CD Workflows | 3 |
| Docker Services | 2 |
| Terraform Resources | 1 |

---

*Document generated automatically by `generate_project_documentation.py`*  
*ParkSmart AI Parking Reservation Platform — Version 4.0*  
*{datetime.now().strftime("%B %d, %Y")}*
"""


# ═══════════════════════════════════════════════════════════════════════
# DOCUMENT ASSEMBLY
# ═══════════════════════════════════════════════════════════════════════

def generate_markdown() -> str:
    """Assemble all sections into a single Markdown document."""
    print("Scanning project structure...")

    sections = [
        section_title_page(),
        section_table_of_contents(),
        section_introduction(),
        section_architecture(),
        section_technology_choices(),
        section_folder_structure(),
        section_file_by_file(),
        section_rag_workflow(),
        section_langgraph_workflow(),
        section_reservation_workflow(),
        section_frontend(),
        section_backend(),
        section_cicd(),
        section_docker(),
        section_terraform(),
        section_security(),
        section_testing(),
        section_future_enhancements(),
        section_code_metrics(),
    ]

    return "\n".join(sections)


# ═══════════════════════════════════════════════════════════════════════
# PDF GENERATION (optional — requires reportlab)
# ═══════════════════════════════════════════════════════════════════════

def generate_pdf(markdown_text: str, output_path: Path) -> bool:
    """Generate PDF from Markdown content using reportlab."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch, mm
        from reportlab.lib.colors import HexColor
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, PageBreak,
            Table, TableStyle, Preformatted, KeepTogether,
        )
    except ImportError:
        print("\n  [!] reportlab not installed. Install with:")
        print("      pip install reportlab")
        print("      Then re-run with --pdf flag.\n")
        return False

    print(f"Generating PDF: {output_path.name}")

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    styles.add(ParagraphStyle(
        "DocTitle",
        parent=styles["Title"],
        fontSize=24,
        spaceAfter=12,
        textColor=HexColor("#1a1a2e"),
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontSize=14,
        spaceAfter=20,
        textColor=HexColor("#4a4a6a"),
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        "SectionH2",
        parent=styles["Heading2"],
        fontSize=16,
        spaceBefore=18,
        spaceAfter=8,
        textColor=HexColor("#16213e"),
        borderWidth=1,
        borderColor=HexColor("#e0e0e0"),
        borderPadding=4,
    ))
    styles.add(ParagraphStyle(
        "SectionH3",
        parent=styles["Heading3"],
        fontSize=13,
        spaceBefore=12,
        spaceAfter=6,
        textColor=HexColor("#1a1a2e"),
    ))
    styles.add(ParagraphStyle(
        "BodyText2",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=6,
        alignment=TA_JUSTIFY,
    ))
    styles.add(ParagraphStyle(
        "CodeBlock",
        parent=styles["Code"],
        fontSize=8,
        leading=10,
        backColor=HexColor("#f5f5f5"),
        borderWidth=0.5,
        borderColor=HexColor("#cccccc"),
        borderPadding=6,
        leftIndent=12,
        rightIndent=12,
        spaceAfter=8,
        spaceBefore=4,
    ))
    styles.add(ParagraphStyle(
        "BulletItem",
        parent=styles["Normal"],
        fontSize=10,
        leading=13,
        leftIndent=24,
        bulletIndent=12,
        spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontSize=9,
        leading=11,
    ))

    story = []
    lines = markdown_text.splitlines()
    i = 0
    in_code_block = False
    code_lines: list[str] = []
    in_table = False
    table_rows: list[list[str]] = []

    def _flush_table():
        nonlocal table_rows, in_table
        if not table_rows:
            return
        # Build reportlab Table
        data = []
        for row in table_rows:
            data.append([Paragraph(cell.strip(), styles["TableCell"]) for cell in row])
        if not data:
            table_rows = []
            in_table = False
            return
        col_count = max(len(r) for r in data)
        # Pad rows
        for r in data:
            while len(r) < col_count:
                r.append(Paragraph("", styles["TableCell"]))
        available = doc.width
        col_w = available / col_count
        t = Table(data, colWidths=[col_w] * col_count)
        t_style = [
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#e8e8f0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#1a1a2e")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
        t.setStyle(TableStyle(t_style))
        story.append(t)
        story.append(Spacer(1, 8))
        table_rows = []
        in_table = False

    def _escape_html(text: str) -> str:
        return (text.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;"))

    def _md_inline(text: str) -> str:
        """Convert inline Markdown to reportlab XML."""
        text = _escape_html(text)
        # Bold
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        # Italic
        text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
        # Inline code
        text = re.sub(r"`([^`]+)`", r'<font face="Courier" size="9">\1</font>', text)
        return text

    while i < len(lines):
        line = lines[i]

        # Code block toggle
        if line.strip().startswith("```"):
            if in_code_block:
                # End code block
                code_text = "\n".join(code_lines)
                if code_text.strip():
                    story.append(Preformatted(
                        _escape_html(code_text), styles["CodeBlock"],
                    ))
                code_lines = []
                in_code_block = False
            else:
                _flush_table()
                in_code_block = True
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        stripped = line.strip()

        # Skip HTML tags and alignment divs
        if stripped.startswith("<") and not stripped.startswith("<b"):
            i += 1
            continue

        # Empty line
        if not stripped:
            if in_table:
                _flush_table()
            i += 1
            continue

        # Headings
        if stripped.startswith("# ") and not stripped.startswith("## "):
            _flush_table()
            story.append(Paragraph(_md_inline(stripped[2:]), styles["DocTitle"]))
            story.append(Spacer(1, 6))
            i += 1
            continue

        if stripped.startswith("## "):
            _flush_table()
            if story:
                story.append(PageBreak())
            story.append(Paragraph(_md_inline(stripped[3:]), styles["SectionH2"]))
            i += 1
            continue

        if stripped.startswith("### "):
            _flush_table()
            story.append(Paragraph(_md_inline(stripped[4:]), styles["SectionH3"]))
            i += 1
            continue

        if stripped.startswith("#### "):
            _flush_table()
            story.append(Spacer(1, 6))
            story.append(Paragraph(
                _md_inline(stripped[5:]),
                ParagraphStyle("h4", parent=styles["Heading4"], fontSize=11,
                               spaceBefore=8, spaceAfter=4),
            ))
            i += 1
            continue

        # Horizontal rule
        if stripped in ("---", "***", "___"):
            _flush_table()
            story.append(Spacer(1, 12))
            i += 1
            continue

        # Table row
        if "|" in stripped and stripped.startswith("|"):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            # Skip separator rows
            if all(re.match(r"^[-:]+$", c) for c in cells):
                i += 1
                continue
            in_table = True
            table_rows.append(cells)
            i += 1
            continue

        # Bullet list
        if stripped.startswith("- ") or stripped.startswith("* "):
            _flush_table()
            text = _md_inline(stripped[2:])
            story.append(Paragraph(f"•  {text}", styles["BulletItem"]))
            i += 1
            continue

        # Numbered list
        m = re.match(r"^(\d+)\.\s+(.*)", stripped)
        if m:
            _flush_table()
            text = _md_inline(m.group(2))
            story.append(Paragraph(f"{m.group(1)}.  {text}", styles["BulletItem"]))
            i += 1
            continue

        # Regular paragraph
        _flush_table()
        story.append(Paragraph(_md_inline(stripped), styles["BodyText2"]))
        i += 1

    _flush_table()

    try:
        doc.build(story)
        return True
    except Exception as e:
        print(f"  [!] PDF generation failed: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    want_pdf = "--pdf" in sys.argv

    # Generate Markdown
    md_content = generate_markdown()
    OUTPUT_MD.write_text(md_content, encoding="utf-8")
    line_count = len(md_content.splitlines())
    print(f"\n  ✔  Markdown generated: {OUTPUT_MD.name}")
    print(f"     {line_count:,} lines of documentation")

    # Generate PDF (optional)
    if want_pdf:
        success = generate_pdf(md_content, OUTPUT_PDF)
        if success:
            size_kb = OUTPUT_PDF.stat().st_size / 1024
            print(f"  ✔  PDF generated: {OUTPUT_PDF.name} ({size_kb:.0f} KB)")
    else:
        print("\n  Tip: Run with --pdf flag to also generate PDF output")
        print("       pip install reportlab  (if not installed)")

    print(f"\n  Output: {OUTPUT_MD}")
    if want_pdf and OUTPUT_PDF.exists():
        print(f"  Output: {OUTPUT_PDF}")
    print()


if __name__ == "__main__":
    main()
