"""
Tests for Stage 3 — MCP Server and MCP Client.

Tests cover:
1. MCP Server:
   - Health check endpoint
   - Tool discovery (POST /mcp/tools/list)
   - Tool execution (POST /mcp/tools/call)
   - API key authentication (reject unauthorized)
   - write_reservation_to_file tool
   - read_approved_reservations tool
   - Error handling (missing args, invalid tool name)

2. MCP Client:
   - write_reservation_to_file via MCP server
   - Fallback to local file when server is down
   - list_tools via server
   - read_approved_reservations via server
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.mcp.mcp_client import MCPClient
from src.mcp.mcp_server import (
    APPROVED_FILE,
    MCP_API_KEY,
    mcp_app,
    tool_read_approved_reservations,
    tool_write_reservation_to_file,
)

# ========================
# MCP SERVER TESTS
# ========================


class TestMCPServer:
    """Tests for the MCP server endpoints."""

    def setup_method(self):
        """Set up test client and temp file for each test."""
        self.client = TestClient(mcp_app)
        self.headers = {"X-MCP-API-KEY": MCP_API_KEY}
        # Use a temp file to avoid polluting the real data directory
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = Path(self.temp_dir) / "test_approved.txt"

    def teardown_method(self):
        """Clean up temp files after each test."""
        if self.temp_file.exists():
            self.temp_file.unlink()
        if Path(self.temp_dir).exists():
            import shutil

            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_health_check(self):
        """Health check should work without authentication."""
        response = self.client.get("/mcp/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["tools_available"] == 2

    def test_list_tools_requires_auth(self):
        """POST /mcp/tools/list should reject requests without API key."""
        response = self.client.post("/mcp/tools/list")
        assert response.status_code == 422  # Missing header

    def test_list_tools_rejects_bad_key(self):
        """POST /mcp/tools/list should reject invalid API keys."""
        response = self.client.post(
            "/mcp/tools/list",
            headers={"X-MCP-API-KEY": "wrong-key"},
        )
        assert response.status_code == 401

    def test_list_tools_success(self):
        """POST /mcp/tools/list should return available tools."""
        response = self.client.post(
            "/mcp/tools/list",
            headers=self.headers,
        )
        assert response.status_code == 200
        data = response.json()
        tools = data["tools"]
        assert len(tools) == 2

        tool_names = [t["name"] for t in tools]
        assert "write_reservation_to_file" in tool_names
        assert "read_approved_reservations" in tool_names

    def test_list_tools_has_parameter_schemas(self):
        """Each tool should include parameter schemas."""
        response = self.client.post(
            "/mcp/tools/list",
            headers=self.headers,
        )
        data = response.json()
        write_tool = [t for t in data["tools"] if t["name"] == "write_reservation_to_file"][0]
        params = write_tool["parameters"]
        param_names = [p["name"] for p in params]
        assert "name" in param_names
        assert "car_number" in param_names
        assert "reservation_period" in param_names

    def test_call_tool_write_reservation(self):
        """POST /mcp/tools/call should write reservation to file."""
        with patch("src.mcp.mcp_server.APPROVED_FILE", self.temp_file):
            response = self.client.post(
                "/mcp/tools/call",
                headers=self.headers,
                json={
                    "tool_name": "write_reservation_to_file",
                    "arguments": {
                        "name": "Test User",
                        "car_number": "ABC-123",
                        "reservation_period": "2026-05-10 09:00 - 2026-05-10 18:00",
                        "approval_time": "2026-05-11 14:30:00",
                    },
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Test User" in data["result"]
        assert data["tool_name"] == "write_reservation_to_file"

    def test_call_tool_invalid_name(self):
        """POST /mcp/tools/call should reject unknown tool names."""
        response = self.client.post(
            "/mcp/tools/call",
            headers=self.headers,
            json={
                "tool_name": "nonexistent_tool",
                "arguments": {},
            },
        )
        assert response.status_code == 404

    def test_call_tool_missing_args(self):
        """POST /mcp/tools/call should reject missing required arguments."""
        response = self.client.post(
            "/mcp/tools/call",
            headers=self.headers,
            json={
                "tool_name": "write_reservation_to_file",
                "arguments": {"name": "Test"},
                # Missing car_number and reservation_period
            },
        )
        assert response.status_code == 400

    def test_call_tool_requires_auth(self):
        """POST /mcp/tools/call should reject unauthorized requests."""
        response = self.client.post(
            "/mcp/tools/call",
            headers={"X-MCP-API-KEY": "bad-key"},
            json={
                "tool_name": "write_reservation_to_file",
                "arguments": {},
            },
        )
        assert response.status_code == 401

    def test_read_approved_no_file(self):
        """read_approved_reservations should handle missing file."""
        with patch("src.mcp.mcp_server.APPROVED_FILE", Path("/nonexistent/file.txt")):
            response = self.client.post(
                "/mcp/tools/call",
                headers=self.headers,
                json={
                    "tool_name": "read_approved_reservations",
                    "arguments": {},
                },
            )
        assert response.status_code == 200
        assert "No approved reservations" in response.json()["result"]


# ========================
# MCP TOOL FUNCTION TESTS
# ========================


class TestMCPToolFunctions:
    """Tests for the tool implementation functions directly."""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = Path(self.temp_dir) / "test_approved.txt"

    def teardown_method(self):
        if Path(self.temp_dir).exists():
            import shutil

            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_write_creates_file_with_header(self):
        """First write should create file with header."""
        with (
            patch("src.mcp.mcp_server.APPROVED_FILE", self.temp_file),
            patch("src.mcp.mcp_server.DATA_DIR", Path(self.temp_dir)),
        ):
            result = tool_write_reservation_to_file(
                {
                    "name": "Himanshu Sachan",
                    "car_number": "UP121",
                    "reservation_period": "2026-05-10 09:00 - 2026-05-10 18:00",
                    "approval_time": "2026-05-11 10:00:00",
                }
            )

        assert "Himanshu Sachan" in result
        content = self.temp_file.read_text()
        assert "APPROVED PARKING RESERVATIONS" in content
        assert "Himanshu Sachan | UP121" in content

    def test_write_appends_multiple_records(self):
        """Multiple writes should append, not overwrite."""
        with (
            patch("src.mcp.mcp_server.APPROVED_FILE", self.temp_file),
            patch("src.mcp.mcp_server.DATA_DIR", Path(self.temp_dir)),
        ):
            tool_write_reservation_to_file(
                {
                    "name": "User One",
                    "car_number": "AAA-111",
                    "reservation_period": "2026-05-10 09:00 - 2026-05-10 18:00",
                }
            )
            tool_write_reservation_to_file(
                {
                    "name": "User Two",
                    "car_number": "BBB-222",
                    "reservation_period": "2026-05-11 09:00 - 2026-05-11 18:00",
                }
            )

        content = self.temp_file.read_text()
        assert "User One | AAA-111" in content
        assert "User Two | BBB-222" in content

    def test_write_missing_name_raises(self):
        """Missing 'name' argument should raise ValueError."""
        with pytest.raises(ValueError, match="name"):
            tool_write_reservation_to_file({"car_number": "X", "reservation_period": "X"})

    def test_read_no_file(self):
        """Reading when file doesn't exist should return helpful message."""
        with patch("src.mcp.mcp_server.APPROVED_FILE", Path("/nonexistent.txt")):
            result = tool_read_approved_reservations({})
        assert "No approved reservations" in result

    def test_read_existing_file(self):
        """Reading existing file should return its contents."""
        self.temp_file.write_text("Test content here")
        with patch("src.mcp.mcp_server.APPROVED_FILE", self.temp_file):
            result = tool_read_approved_reservations({})
        assert "Test content here" in result


# ========================
# MCP CLIENT TESTS
# ========================


class TestMCPClient:
    """Tests for the MCP client (with mocked HTTP calls)."""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = Path(self.temp_dir) / "test_fallback.txt"
        self.client = MCPClient(
            server_url="http://localhost:8001",
            api_key=MCP_API_KEY,
        )
        self.client.fallback_file = self.temp_file

    def teardown_method(self):
        if Path(self.temp_dir).exists():
            import shutil

            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_fallback_write_when_server_down(self):
        """When MCP server is unreachable, client should write file locally."""
        result = self.client.write_reservation_to_file(
            name="Fallback User",
            car_number="FB-999",
            reservation_period="2026-05-10 09:00 - 2026-05-10 18:00",
        )

        assert "Fallback" in result or "fallback" in result.lower() or "MCP" in result
        assert self.temp_file.exists()
        content = self.temp_file.read_text()
        assert "Fallback User | FB-999" in content

    def test_fallback_creates_header(self):
        """Fallback write should create file with header on first write."""
        self.client._fallback_write(
            {
                "name": "Test",
                "car_number": "T-1",
                "reservation_period": "2026-01-01 09:00 - 2026-01-01 18:00",
                "approval_time": "2026-01-01 10:00:00",
            },
            "server down",
        )

        content = self.temp_file.read_text()
        assert "APPROVED PARKING RESERVATIONS" in content
        assert "Test | T-1" in content

    @patch("src.mcp.mcp_client.httpx.Client")
    def test_write_via_mcp_server(self, mock_httpx_class):
        """When MCP server is available, client should call it via HTTP."""
        # Mock successful MCP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "tool_name": "write_reservation_to_file",
            "result": "Reservation written to file: Test | T-1 | ...",
            "timestamp": "2026-05-11T10:00:00",
        }
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_httpx_class.return_value = mock_client_instance

        result = self.client.write_reservation_to_file(
            name="Test User",
            car_number="T-1",
            reservation_period="2026-05-10 09:00 - 2026-05-10 18:00",
        )

        assert "MCP" in result
        assert "Written to file" in result or "written" in result.lower()
        # Verify the HTTP call was made
        mock_client_instance.post.assert_called_once()

    @patch("src.mcp.mcp_client.httpx.Client")
    def test_list_tools_via_server(self, mock_httpx_class):
        """Client should be able to list tools from the server."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tools": [
                {"name": "write_reservation_to_file", "description": "Write...", "parameters": []},
                {"name": "read_approved_reservations", "description": "Read...", "parameters": []},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_httpx_class.return_value = mock_client_instance

        tools = self.client.list_tools()
        assert len(tools) == 2
        assert tools[0]["name"] == "write_reservation_to_file"

    def test_read_approved_fallback(self):
        """Read should fall back to local file when server is down."""
        self.temp_file.write_text("Local content")
        result = self.client.read_approved_reservations()
        assert "Local content" in result

    def test_read_approved_no_file(self):
        """Read fallback should return message when no file exists."""
        result = self.client.read_approved_reservations()
        assert "No approved reservations" in result
