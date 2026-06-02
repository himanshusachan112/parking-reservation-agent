"""
MCP Server — Model Context Protocol Server for Parking Reservations.

This is the Stage 3 MCP server built with FastAPI. It implements the MCP protocol
so that LLM agents can DISCOVER and CALL tools over the network.

MCP PROTOCOL OVERVIEW:
- MCP is a standard by Anthropic for connecting LLM agents to external tools.
- Instead of hardcoding tools inside the agent, tools are exposed as a separate
  server that any MCP-compatible client can discover and call.
- The protocol uses JSON-RPC style messages:
    1. Client calls POST /mcp/tools/list  → gets back available tools + schemas
    2. Client calls POST /mcp/tools/call  → executes a specific tool with arguments
- This decouples agents from tool implementations.

WHAT THIS SERVER DOES:
- Exposes a tool called "write_reservation_to_file" that writes approved
  reservation details to a text file (data/approved_reservations.txt).
- File entry format: Name | Car Number | Reservation Period | Approval Time
- Secured with API key authentication (MCP_API_KEY header).

WHY A SEPARATE SERVER?
- The task says: "develop a simple MCP server using Python + FastAPI"
- Separating the file-writing into an MCP server means:
  1. Any agent (admin CLI, REST API, future agents) can call it
  2. The tool is discoverable — agents can ask "what tools do you have?"
  3. The server can be deployed independently from the agents
  4. Security is centralized (one API key gate for all tool access)

HOW TO RUN:
    python main.py --mcp-server     (starts on port 8001)
    or: uvicorn src.mcp.mcp_server:mcp_app --host 0.0.0.0 --port 8001
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

# ========================
# CONFIGURATION
# ========================

# Where to write approved reservation records
DATA_DIR = Path(__file__).parent.parent.parent / "data"
APPROVED_FILE = DATA_DIR / "approved_reservations.txt"

# API key for securing the MCP server — loaded from environment
# The admin agent and REST API must send this key in the X-MCP-API-KEY header
MCP_API_KEY = os.environ.get("MCP_API_KEY", "mcp-parksmart-secret-key-2026")


# ========================
# PYDANTIC MODELS (JSON-RPC style)
# ========================


class ToolParameter(BaseModel):
    """Schema for a single tool parameter."""

    name: str
    type: str
    description: str
    required: bool = True


class ToolDefinition(BaseModel):
    """Schema describing a tool that this MCP server exposes."""

    name: str = Field(description="Unique tool name")
    description: str = Field(description="What the tool does")
    parameters: List[ToolParameter] = Field(description="Expected input parameters")


class ToolsListResponse(BaseModel):
    """Response for POST /mcp/tools/list — returns all available tools."""

    tools: List[ToolDefinition]


class ToolCallRequest(BaseModel):
    """Request body for POST /mcp/tools/call — invoke a specific tool."""

    tool_name: str = Field(description="Name of the tool to call")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments to pass to the tool")


class ToolCallResponse(BaseModel):
    """Response for POST /mcp/tools/call — result of tool execution."""

    success: bool
    tool_name: str
    result: str
    timestamp: str


# ========================
# API KEY AUTHENTICATION
# ========================


def verify_api_key(x_mcp_api_key: str = Header(..., alias="X-MCP-API-KEY")):
    """
    Dependency that verifies the API key on every request.

    The client must send the correct key in the X-MCP-API-KEY header.
    This prevents unauthorized access to the MCP tools.

    Why a header-based key?
    - Simple and effective for server-to-server communication
    - The key is never exposed in URLs or logs
    - Easy to rotate — just change the env variable
    """
    if x_mcp_api_key != MCP_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid MCP API key. Access denied.")
    return x_mcp_api_key


# ========================
# TOOL REGISTRY
# ========================
# This is the registry of all tools this MCP server exposes.
# Each tool is a Python function with a defined schema.
# Adding a new tool = adding a function + registering it here.

TOOLS_REGISTRY: Dict[str, ToolDefinition] = {
    "write_reservation_to_file": ToolDefinition(
        name="write_reservation_to_file",
        description=(
            "Write an approved parking reservation to the approved_reservations.txt file. "
            "Called after an administrator approves a reservation. "
            "Format: Name | Car Number | Reservation Period | Approval Time"
        ),
        parameters=[
            ToolParameter(name="name", type="string", description="Full name of the person (first and last name)"),
            ToolParameter(name="car_number", type="string", description="Vehicle registration / license plate number"),
            ToolParameter(
                name="reservation_period",
                type="string",
                description="Reservation period string, e.g. '2026-05-10 09:00 - 2026-05-10 18:00'",
            ),
            ToolParameter(
                name="approval_time",
                type="string",
                description="Timestamp when the reservation was approved (ISO format)",
                required=False,
            ),
        ],
    ),
    "read_approved_reservations": ToolDefinition(
        name="read_approved_reservations",
        description=(
            "Read all approved reservation records from the approved_reservations.txt file. "
            "Returns the file contents as a string."
        ),
        parameters=[],
    ),
}


# ========================
# TOOL IMPLEMENTATIONS
# ========================


def tool_write_reservation_to_file(arguments: Dict[str, Any]) -> str:
    """
    Write a single approved reservation record to the text file.

    This is the core tool of Stage 3. When the admin approves a reservation:
    1. The admin agent/REST API calls the MCP client
    2. The MCP client sends a POST /mcp/tools/call to this server
    3. This function writes the record to data/approved_reservations.txt

    File format (one line per reservation):
        Name | Car Number | Reservation Period | Approval Time

    Example:
        Himanshu Sachan | UP121 | 2026-05-10 09:00 - 2026-05-10 18:00 | 2026-05-11 14:30:00
    """
    # Validate required arguments
    name = arguments.get("name")
    car_number = arguments.get("car_number")
    reservation_period = arguments.get("reservation_period")
    approval_time = arguments.get("approval_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    if not name:
        raise ValueError("Missing required argument: 'name'")
    if not car_number:
        raise ValueError("Missing required argument: 'car_number'")
    if not reservation_period:
        raise ValueError("Missing required argument: 'reservation_period'")

    # Ensure the data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Build the record line
    record = f"{name} | {car_number} | {reservation_period} | {approval_time}"

    # Write header if file doesn't exist yet
    if not APPROVED_FILE.exists():
        with open(APPROVED_FILE, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write("  APPROVED PARKING RESERVATIONS — ParkSmart\n")
            f.write("=" * 80 + "\n")
            f.write(f"{'Name':<25} | {'Car Number':<12} | {'Reservation Period':<40} | {'Approval Time'}\n")
            f.write("-" * 80 + "\n")

    # Append the reservation record
    with open(APPROVED_FILE, "a", encoding="utf-8") as f:
        f.write(record + "\n")

    return f"Reservation written to file: {record}"


def tool_read_approved_reservations(arguments: Dict[str, Any]) -> str:
    """
    Read all approved reservation records from the file.

    Returns the full contents of approved_reservations.txt.
    If the file doesn't exist, returns a message saying no records found.
    """
    if not APPROVED_FILE.exists():
        return "No approved reservations file found. No reservations have been approved yet."

    with open(APPROVED_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    if not content.strip():
        return "The approved reservations file is empty."

    return content


# Map tool names to their implementation functions
TOOL_FUNCTIONS = {
    "write_reservation_to_file": tool_write_reservation_to_file,
    "read_approved_reservations": tool_read_approved_reservations,
}


# ========================
# FASTAPI MCP SERVER
# ========================

mcp_app = FastAPI(
    title="ParkSmart MCP Server",
    description=(
        "Model Context Protocol (MCP) server for the ParkSmart Parking System.\n\n"
        "This server exposes tools that LLM agents can discover and call.\n"
        "Secured with API key authentication (X-MCP-API-KEY header)."
    ),
    version="1.0.0",
)


@mcp_app.get("/")
def root():
    """Root path returns basic MCP server status and useful links."""
    return {
        "status": "running",
        "service": "ParkSmart MCP Server",
        "message": "Use /mcp/health for health checks or /docs for API documentation.",
        "health_endpoint": "/mcp/health",
        "docs": "/docs",
        "tools_list": "/mcp/tools/list",
    }


@mcp_app.get("/mcp/health")
def mcp_health():
    """
    Health check endpoint (no auth required).

    Used by clients to verify the MCP server is running before calling tools.
    """
    return {
        "status": "healthy",
        "service": "ParkSmart MCP Server",
        "tools_available": len(TOOLS_REGISTRY),
        "timestamp": datetime.now().isoformat(),
    }


@mcp_app.post("/mcp/tools/list", response_model=ToolsListResponse)
def list_tools(api_key: str = Depends(verify_api_key)):
    """
    MCP Tool Discovery — List all available tools.

    This is the first step in the MCP protocol. The client (agent) calls this
    endpoint to discover what tools are available and what arguments they expect.

    The response includes:
    - Tool name (used to call it)
    - Description (so the LLM knows what the tool does)
    - Parameter schemas (so the LLM knows what arguments to pass)

    Requires: X-MCP-API-KEY header
    """
    return ToolsListResponse(tools=list(TOOLS_REGISTRY.values()))


@mcp_app.post("/mcp/tools/call", response_model=ToolCallResponse)
def call_tool(request: ToolCallRequest, api_key: str = Depends(verify_api_key)):
    """
    MCP Tool Execution — Call a specific tool with arguments.

    This is the second step in the MCP protocol. After discovering tools via
    /mcp/tools/list, the client calls this endpoint to execute a tool.

    The request body contains:
    - tool_name: which tool to run (must match a name from /mcp/tools/list)
    - arguments: dict of key-value pairs matching the tool's parameter schema

    The response contains:
    - success: whether the tool executed without error
    - result: the tool's return value (string)
    - timestamp: when the tool was executed

    Requires: X-MCP-API-KEY header
    """
    # Check if the requested tool exists
    if request.tool_name not in TOOL_FUNCTIONS:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{request.tool_name}' not found. " f"Available tools: {list(TOOL_FUNCTIONS.keys())}",
        )

    # Execute the tool
    tool_fn = TOOL_FUNCTIONS[request.tool_name]
    try:
        result = tool_fn(request.arguments)
    except ValueError as e:
        # Missing or invalid arguments
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}")

    return ToolCallResponse(
        success=True,
        tool_name=request.tool_name,
        result=result,
        timestamp=datetime.now().isoformat(),
    )
