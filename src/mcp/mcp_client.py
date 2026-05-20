"""
MCP Client — Connects agents to the MCP Server.

This client is used by the admin agent and REST API to call MCP tools
over the network. It implements the client side of the MCP protocol.

MCP CLIENT FLOW:
1. Client connects to the MCP server (checks health)
2. Client discovers tools (POST /mcp/tools/list)
3. Client calls a tool (POST /mcp/tools/call) with arguments
4. Server executes the tool and returns the result

WHY A SEPARATE CLIENT CLASS?
- Encapsulates all MCP communication logic in one place
- Both the admin agent and REST API use the same client
- Handles authentication (API key), errors, and retries
- If the MCP server is down, falls back to a local file write

USAGE:
    from src.mcp.mcp_client import MCPClient

    client = MCPClient()

    # Discover tools
    tools = client.list_tools()

    # Write a reservation to file
    result = client.write_reservation_to_file(
        name="Himanshu Sachan",
        car_number="UP121",
        reservation_period="2026-05-10 09:00 - 2026-05-10 18:00",
    )
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx


class MCPClient:
    """
    Client for communicating with the ParkSmart MCP Server.

    This class is used by the admin agent and REST API to call MCP tools.
    It handles:
    - Server health checks
    - Tool discovery (list available tools)
    - Tool execution (call a specific tool with arguments)
    - Authentication (sends API key in headers)
    - Fallback to local file write if MCP server is unreachable
    """

    def __init__(
        self,
        server_url: str = None,
        api_key: str = None,
        timeout: float = 10.0,
    ):
        """
        Initialize the MCP client.

        Args:
            server_url: Base URL of the MCP server (default: http://localhost:8001)
            api_key: API key for authentication (default: from MCP_API_KEY env var)
            timeout: Request timeout in seconds
        """
        self.server_url = server_url or os.environ.get("MCP_SERVER_URL", "http://localhost:8001")
        self.api_key = api_key or os.environ.get("MCP_API_KEY", "mcp-parksmart-secret-key-2026")
        self.timeout = timeout

        # HTTP headers for every request
        self.headers = {
            "X-MCP-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

        # Fallback file path (same as server uses)
        self.fallback_file = Path(__file__).parent.parent.parent / "data" / "approved_reservations.txt"

    def is_server_available(self) -> bool:
        """
        Check if the MCP server is running and healthy.

        Calls GET /mcp/health (no auth required).
        Returns True if the server responds with status 200.
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.server_url}/mcp/health")
                return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        Discover available tools on the MCP server.

        Calls POST /mcp/tools/list to get the list of tools with their
        names, descriptions, and parameter schemas.

        Returns:
            List of tool definitions (dicts with name, description, parameters)

        Raises:
            ConnectionError: If the MCP server is unreachable
            PermissionError: If the API key is invalid
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.server_url}/mcp/tools/list",
                    headers=self.headers,
                )

            if response.status_code == 401:
                raise PermissionError("Invalid MCP API key. Check MCP_API_KEY.")

            response.raise_for_status()
            data = response.json()
            return data.get("tools", [])

        except httpx.ConnectError:
            raise ConnectionError(
                f"MCP server not reachable at {self.server_url}. " "Start it with: python main.py --mcp-server"
            )

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a specific tool on the MCP server.

        Sends POST /mcp/tools/call with the tool name and arguments.
        The server executes the tool and returns the result.

        Args:
            tool_name: Name of the tool to call (from list_tools())
            arguments: Dict of arguments matching the tool's parameter schema

        Returns:
            Dict with success, tool_name, result, timestamp

        Raises:
            ConnectionError: If the MCP server is unreachable
            PermissionError: If the API key is invalid
            ValueError: If the tool name is invalid or arguments are wrong
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.server_url}/mcp/tools/call",
                    headers=self.headers,
                    json={
                        "tool_name": tool_name,
                        "arguments": arguments,
                    },
                )

            if response.status_code == 401:
                raise PermissionError("Invalid MCP API key. Check MCP_API_KEY.")
            if response.status_code == 404:
                raise ValueError(f"Tool '{tool_name}' not found on MCP server.")
            if response.status_code == 400:
                raise ValueError(f"Invalid arguments: {response.json().get('detail', '')}")

            response.raise_for_status()
            return response.json()

        except httpx.ConnectError:
            raise ConnectionError(
                f"MCP server not reachable at {self.server_url}. " "Start it with: python main.py --mcp-server"
            )

    def write_reservation_to_file(
        self,
        name: str,
        car_number: str,
        reservation_period: str,
        approval_time: str = None,
    ) -> str:
        """
        High-level method: Write an approved reservation to file via MCP.

        This is the main method called by the admin agent and REST API
        when a reservation is approved. It:
        1. Tries to call the MCP server's write_reservation_to_file tool
        2. If the MCP server is down, falls back to writing the file locally

        Args:
            name: Full name (e.g., "Himanshu Sachan")
            car_number: Vehicle registration (e.g., "UP121")
            reservation_period: Period string (e.g., "2026-05-10 09:00 - 2026-05-10 18:00")
            approval_time: When approved (auto-generated if not provided)

        Returns:
            Status message indicating success (via MCP or fallback)
        """
        if not approval_time:
            approval_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        arguments = {
            "name": name,
            "car_number": car_number,
            "reservation_period": reservation_period,
            "approval_time": approval_time,
        }

        # Try MCP server first
        try:
            result = self.call_tool("write_reservation_to_file", arguments)
            return f"✓ MCP: {result.get('result', 'Written to file')}"
        except (ConnectionError, Exception) as e:
            # Fallback: write directly to file if MCP server is down
            return self._fallback_write(arguments, str(e))

    def _fallback_write(self, arguments: Dict[str, Any], error_msg: str) -> str:
        """
        Fallback: Write reservation to file locally when MCP server is unreachable.

        This ensures reservations are never lost even if the MCP server is down.
        The file format is identical to what the MCP server writes.

        Args:
            arguments: Same dict that would have been sent to MCP
            error_msg: The error that caused the fallback

        Returns:
            Status message indicating fallback was used
        """
        name = arguments["name"]
        car_number = arguments["car_number"]
        reservation_period = arguments["reservation_period"]
        approval_time = arguments["approval_time"]

        record = f"{name} | {car_number} | {reservation_period} | {approval_time}"

        # Ensure data directory exists
        self.fallback_file.parent.mkdir(parents=True, exist_ok=True)

        # Write header if file doesn't exist
        if not self.fallback_file.exists():
            with open(self.fallback_file, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write("  APPROVED PARKING RESERVATIONS — ParkSmart\n")
                f.write("=" * 80 + "\n")
                f.write(f"{'Name':<25} | {'Car Number':<12} | {'Reservation Period':<40} | {'Approval Time'}\n")
                f.write("-" * 80 + "\n")

        # Append the record
        with open(self.fallback_file, "a", encoding="utf-8") as f:
            f.write(record + "\n")

        return f"⚠ MCP server unavailable ({error_msg}). " f"Fallback: wrote directly to file: {record}"

    def read_approved_reservations(self) -> str:
        """
        Read all approved reservations from the MCP server.

        Calls the read_approved_reservations tool on the MCP server.
        Falls back to reading the local file if server is unreachable.

        Returns:
            Contents of the approved reservations file
        """
        try:
            result = self.call_tool("read_approved_reservations", {})
            return result.get("result", "No data")
        except (ConnectionError, Exception):
            # Fallback: read local file
            if self.fallback_file.exists():
                with open(self.fallback_file, "r", encoding="utf-8") as f:
                    return f.read()
            return "No approved reservations found."
