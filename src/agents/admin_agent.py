"""
Admin Agent Module - Human-in-the-Loop Reservation Approval.

This is the SECOND AGENT required by Stage 2. It provides an interface
for a human administrator to review and approve/reject parking reservations.

HOW IT WORKS:
1. The admin agent fetches pending reservations (from the REST API or directly from DB)
2. Presents each reservation to the admin with relevant context
3. Uses LangChain tools to help the admin make decisions:
   - Check current parking availability
   - Check for scheduling conflicts
   - View reservation details
4. Admin decides: approve or reject (with optional notes)
5. Decision is saved back to the database

WHY A LANGCHAIN AGENT?
- The task says "Create the second agent using LangChain"
- LangChain agents can use TOOLS to look up information before making decisions
- The LLM helps format information and can flag potential issues
- The admin still makes the final decision (human-in-the-loop)

TWO MODES OF OPERATION:
1. CLI Mode: Admin runs `python main.py --admin` and reviews via terminal
2. API Mode: Admin uses the REST API endpoints directly (Swagger UI)
"""

import os
import sys
from typing import Any, Dict, List, Optional

import requests
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI

from config.settings import settings
from src.database.sql_store import SQLStore
from src.mcp.mcp_client import MCPClient
from src.notifications.email_service import EmailService
from src.utils.masking import mask_email

# ========================
# ADMIN AGENT TOOLS
# ========================
# These are LangChain "tools" that the agent can call to gather information.
# Each tool is a function decorated with @tool that the LLM can invoke.


def create_check_availability_tool(sql_store: SQLStore):
    """Create a tool that checks parking space availability."""

    @tool
    def check_availability(space_type: str = "all") -> str:
        """Check current parking space availability. Pass space_type like 'standard', 'large', 'ev', 'vip', or 'all'."""
        availability = sql_store.get_total_availability()
        if space_type != "all" and space_type in availability:
            info = availability[space_type]
            return f"{space_type.title()}: {info['available']}/{info['total']} spaces available"

        lines = []
        for stype, info in availability.items():
            lines.append(f"  {stype.title()}: {info['available']}/{info['total']} available")
        return "Current Availability:\n" + "\n".join(lines)

    return check_availability


def create_get_reservation_tool(sql_store: SQLStore):
    """Create a tool that fetches reservation details by ID."""

    @tool
    def get_reservation(reservation_id: int) -> str:
        """Get details of a specific reservation by its ID number."""
        r = sql_store.get_reservation_by_id(reservation_id)
        if not r:
            return f"Reservation #{reservation_id} not found."
        return (
            f"Reservation #{r['id']}:\n"
            f"  Name: {r['first_name']} {r['last_name']}\n"
            f"  Email: {mask_email(r.get('email', '') or '')}\n"
            f"  Vehicle: {r['car_number']}\n"
            f"  Space: {r['space_type']}\n"
            f"  Period: {r['start_datetime']} → {r['end_datetime']}\n"
            f"  Status: {r['status']}\n"
            f"  Created: {r['created_at']}"
        )

    return get_reservation


def create_list_pending_tool(sql_store: SQLStore):
    """Create a tool that lists all pending reservations."""

    @tool
    def list_pending_reservations() -> str:
        """List all pending reservation requests waiting for admin review."""
        reservations = sql_store.get_reservations(status="pending")
        if not reservations:
            return "No pending reservations to review."

        lines = [f"Found {len(reservations)} pending reservation(s):\n"]
        for r in reservations:
            lines.append(
                f"  #{r['id']} | {r['first_name']} {r['last_name']} | "
                f"{r['car_number']} | {r['space_type']} | "
                f"{r['start_datetime']} → {r['end_datetime']}"
            )
        return "\n".join(lines)

    return list_pending_reservations


# ========================
# ADMIN AGENT CLASS
# ========================


class AdminAgent:
    """
    LangChain-powered admin agent for reviewing parking reservations.

    This is the second agent in the system. It provides the human administrator
    with an intelligent interface to review, approve, and reject reservations.

    The agent uses LangChain tools to:
    - Check parking availability before approving
    - Look up reservation details
    - List all pending reservations

    The admin makes the final decision (human-in-the-loop).
    """

    def __init__(self, sql_store: SQLStore = None):
        """
        Initialize the admin agent.

        Args:
            sql_store: SQLStore instance (or creates a new one)
        """
        self.sql_store = sql_store or SQLStore()
        self.email_service = EmailService()
        self.mcp_client = MCPClient()

        # Initialize the LLM (same EPAM DIAL as user chatbot)
        self.llm = AzureChatOpenAI(
            azure_deployment=settings.llm_model,
            azure_endpoint=settings.azure_endpoint,
            api_key=settings.dial_api_key,
            api_version=settings.api_version,
            temperature=0.2,  # Lower temp for admin decisions
            max_tokens=1024,
        )

        # Create LangChain tools
        self.tools = [
            create_check_availability_tool(self.sql_store),
            create_list_pending_tool(self.sql_store),
            create_get_reservation_tool(self.sql_store),
        ]

        # Bind tools to the LLM so it can call them
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # Admin prompt — instructs the LLM to help the admin
        self.system_prompt = (
            "You are an administrative assistant for ParkSmart Parking.\n"
            "Your job is to help the admin review parking reservation requests.\n\n"
            "For each reservation, you should:\n"
            "1. Check if parking spaces are available for the requested type\n"
            "2. Summarize the reservation details clearly\n"
            "3. Flag any potential issues (e.g., no availability, unusual times)\n"
            "4. Present a recommendation but let the admin make the final decision\n\n"
            "Always be concise and professional."
        )

    def get_pending_reservations(self) -> List[Dict[str, Any]]:
        """
        Fetch all pending reservations from the database.

        Returns:
            List of reservation dicts with status='pending'
        """
        return self.sql_store.get_reservations(status="pending")

    def review_reservation(self, reservation_id: int) -> str:
        """
        Use the LLM to generate a review summary for a reservation.

        The LLM checks availability and provides a recommendation.

        Args:
            reservation_id: The ID of the reservation to review

        Returns:
            A formatted review summary string
        """
        reservation = self.sql_store.get_reservation_by_id(reservation_id)
        if not reservation:
            return f"Reservation #{reservation_id} not found."

        # Get current availability for context
        availability = self.sql_store.get_total_availability()
        space_type = reservation["space_type"]
        avail_info = availability.get(space_type, {"available": 0, "total": 0})

        review = (
            f"═══ RESERVATION REVIEW ═══\n"
            f"ID: #{reservation['id']}\n"
            f"Name: {reservation['first_name']} {reservation['last_name']}\n"
            f"Email: {mask_email(reservation.get('email', '') or '')}\n"
            f"Vehicle: {reservation['car_number']}\n"
            f"Space Type: {reservation['space_type'].upper()}\n"
            f"Period: {reservation['start_datetime']} → {reservation['end_datetime']}\n"
            f"Submitted: {reservation['created_at']}\n"
            f"\n"
            f"── Availability Check ──\n"
            f"{space_type.title()} spaces: {avail_info['available']}/{avail_info['total']} available\n"
        )

        if avail_info["available"] > 0:
            review += f"✅ Spaces available — safe to approve.\n"
        else:
            review += f"⚠️ NO {space_type.upper()} SPACES AVAILABLE — consider rejecting.\n"

        return review

    def approve_reservation(self, reservation_id: int, admin_notes: str = None) -> str:
        """
        Approve a pending reservation.

        Updates the reservation status to 'approved' in the database.

        Args:
            reservation_id: The reservation to approve
            admin_notes: Optional notes from the admin

        Returns:
            Confirmation message
        """
        reservation = self.sql_store.get_reservation_by_id(reservation_id)
        if not reservation:
            return f"❌ Reservation #{reservation_id} not found."

        if reservation["status"] != "pending":
            return f"❌ Reservation #{reservation_id} is already {reservation['status']}."

        success = self.sql_store.update_reservation_status(reservation_id, "approved", admin_notes)

        if success:
            # Notify the user via email about the approval
            try:
                updated = self.sql_store.get_reservation_by_id(reservation_id)
                self.email_service.notify_user_status_change(updated)
            except Exception as e:
                print(f"⚠ User notification failed: {e}")

            # Write approved reservation to file via MCP server (Stage 3)
            try:
                mcp_result = self.mcp_client.write_reservation_to_file(
                    name=f"{reservation['first_name']} {reservation['last_name']}",
                    car_number=reservation["car_number"],
                    reservation_period=(f"{reservation['start_datetime']} - {reservation['end_datetime']}"),
                )
                print(f"  {mcp_result}")
            except Exception as e:
                print(f"⚠ MCP file write failed: {e}")

            return (
                f"✅ Reservation #{reservation_id} APPROVED.\n"
                f"   {reservation['first_name']} {reservation['last_name']} | "
                f"{reservation['space_type']} | "
                f"{reservation['start_datetime']} → {reservation['end_datetime']}"
            )
        return f"❌ Failed to approve reservation #{reservation_id}."

    def reject_reservation(self, reservation_id: int, admin_notes: str = None) -> str:
        """
        Reject a pending reservation.

        Updates the reservation status to 'rejected' in the database.

        Args:
            reservation_id: The reservation to reject
            admin_notes: Reason for rejection

        Returns:
            Confirmation message
        """
        reservation = self.sql_store.get_reservation_by_id(reservation_id)
        if not reservation:
            return f"❌ Reservation #{reservation_id} not found."

        if reservation["status"] != "pending":
            return f"❌ Reservation #{reservation_id} is already {reservation['status']}."

        success = self.sql_store.update_reservation_status(reservation_id, "rejected", admin_notes)

        if success:
            # Notify the user via email about the rejection
            try:
                updated = self.sql_store.get_reservation_by_id(reservation_id)
                self.email_service.notify_user_status_change(updated)
            except Exception as e:
                print(f"⚠ User notification failed: {e}")

            return (
                f"🚫 Reservation #{reservation_id} REJECTED.\n"
                f"   {reservation['first_name']} {reservation['last_name']} | "
                f"Reason: {admin_notes or 'No reason provided'}"
            )
        return f"❌ Failed to reject reservation #{reservation_id}."

    def get_admin_summary(self) -> str:
        """
        Generate a summary of all reservations for the admin dashboard.

        Returns:
            Formatted summary string with counts by status
        """
        all_reservations = self.sql_store.get_reservations()
        pending = [r for r in all_reservations if r["status"] == "pending"]
        approved = [r for r in all_reservations if r["status"] == "approved"]
        rejected = [r for r in all_reservations if r["status"] == "rejected"]

        summary = (
            f"═══ ADMIN DASHBOARD ═══\n"
            f"Total Reservations: {len(all_reservations)}\n"
            f"  ⏳ Pending:  {len(pending)}\n"
            f"  ✅ Approved: {len(approved)}\n"
            f"  🚫 Rejected: {len(rejected)}\n"
        )

        if pending:
            summary += f"\n── Pending Reservations ──\n"
            for r in pending:
                summary += (
                    f"  #{r['id']} | {r['first_name']} {r['last_name']} | "
                    f"{r['car_number']} | {r['space_type']} | "
                    f"{r['start_datetime']} → {r['end_datetime']}\n"
                )

        return summary


def run_admin_cli():
    """
    Run the admin agent in CLI (terminal) mode.

    This provides an interactive terminal interface for the administrator
    to review and process pending reservation requests.

    The admin can:
    - View all pending reservations
    - Review individual reservations (with availability check)
    - Approve or reject reservations with notes
    """
    print("=" * 55)
    print("  🔧 PARKSMART ADMIN PANEL")
    print("=" * 55)

    agent = AdminAgent()

    print("\nCommands:")
    print("  list     - Show all pending reservations")
    print("  all      - Show all reservations (any status)")
    print("  review N - Review reservation #N with availability check")
    print("  approve N [notes] - Approve reservation #N")
    print("  reject N [notes]  - Reject reservation #N")
    print("  dash     - Show admin dashboard summary")
    print("  quit     - Exit admin panel")
    print("-" * 55)

    while True:
        try:
            cmd = input("\n🔧 Admin: ").strip()

            if not cmd:
                continue

            if cmd.lower() == "quit":
                print("\nAdmin panel closed. 👋")
                break

            elif cmd.lower() == "list":
                # Show pending reservations
                pending = agent.get_pending_reservations()
                if not pending:
                    print("\n  No pending reservations. All caught up! ✅")
                else:
                    print(f"\n  Found {len(pending)} pending reservation(s):\n")
                    for r in pending:
                        print(
                            f"  #{r['id']} | {r['first_name']} {r['last_name']} | "
                            f"{r['car_number']} | {r['space_type']} | "
                            f"{r['start_datetime']} → {r['end_datetime']}"
                        )

            elif cmd.lower() == "all":
                # Show all reservations
                all_res = agent.sql_store.get_reservations()
                if not all_res:
                    print("\n  No reservations found.")
                else:
                    print(f"\n  Total: {len(all_res)} reservation(s):\n")
                    for r in all_res:
                        status_icon = {"pending": "⏳", "approved": "✅", "rejected": "🚫"}.get(r["status"], "?")
                        print(
                            f"  {status_icon} #{r['id']} | {r['first_name']} {r['last_name']} | "
                            f"{r['car_number']} | {r['space_type']} | {r['status']}"
                        )

            elif cmd.lower() == "dash":
                print(f"\n{agent.get_admin_summary()}")

            elif cmd.lower().startswith("review"):
                parts = cmd.split()
                if len(parts) < 2:
                    print("  Usage: review <id>  (e.g., 'review 1')")
                    continue
                try:
                    rid = int(parts[1])
                    print(f"\n{agent.review_reservation(rid)}")
                except ValueError:
                    print("  Invalid ID. Use a number (e.g., 'review 1').")

            elif cmd.lower().startswith("approve"):
                parts = cmd.split(maxsplit=2)
                if len(parts) < 2:
                    print("  Usage: approve <id> [notes]  (e.g., 'approve 1 VIP customer')")
                    continue
                try:
                    rid = int(parts[1])
                    notes = parts[2] if len(parts) > 2 else None
                    result = agent.approve_reservation(rid, notes)
                    print(f"\n{result}")
                except ValueError:
                    print("  Invalid ID. Use a number (e.g., 'approve 1').")

            elif cmd.lower().startswith("reject"):
                parts = cmd.split(maxsplit=2)
                if len(parts) < 2:
                    print("  Usage: reject <id> [reason]  (e.g., 'reject 1 No spaces')")
                    continue
                try:
                    rid = int(parts[1])
                    notes = parts[2] if len(parts) > 2 else None
                    result = agent.reject_reservation(rid, notes)
                    print(f"\n{result}")
                except ValueError:
                    print("  Invalid ID. Use a number (e.g., 'reject 1').")

            else:
                print("  Unknown command. Type 'list', 'review N', 'approve N', 'reject N', 'dash', or 'quit'.")

        except KeyboardInterrupt:
            print("\n\nAdmin panel closed. 👋")
            break
        except Exception as e:
            print(f"\n  ❌ Error: {e}")


if __name__ == "__main__":
    run_admin_cli()
