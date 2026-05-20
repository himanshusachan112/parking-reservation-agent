"""
LangGraph State Schema — Defines the Data Flowing Through the Graph.

This module defines the TypedDict that serves as the "state" for the
LangGraph orchestration graph. Every node in the graph reads from and
writes to this shared state.

WHY A TYPED STATE?
- LangGraph requires a typed state schema so it knows what data flows
  between nodes.
- Each node receives the FULL state, modifies relevant fields, and
  returns the updated state.
- This replaces the manual "pass data between separate programs" approach.

STATE FIELDS:
- user_message: The latest message from the user
- bot_response: The chatbot's response to show the user
- conversation_phase: Where we are in the overall pipeline
- reservation_data: Collected booking info (name, car, dates, etc.)
- reservation_id: DB id after reservation is saved
- admin_decision: "approve" or "reject" (set by admin node)
- admin_notes: Optional notes from the admin
- notification_sent: Whether email notification was sent
- mcp_recorded: Whether the MCP file write succeeded
- error: Any error message during processing
- history: List of (role, message) tuples for conversation context
"""

from enum import Enum
from typing import Any, List, Literal, Optional, Tuple, TypedDict


class PipelinePhase(str, Enum):
    """
    Tracks where the reservation is in the overall pipeline.

    This replaces the old approach of running separate programs:
    - chatbot CLI → user_interaction
    - admin CLI → awaiting_admin / admin_reviewing
    - email service → notifying
    - MCP client → recording
    - Now all orchestrated in one graph!
    """

    USER_INTERACTION = "user_interaction"  # Chatbot is talking to user
    BOOKING_COMPLETE = "booking_complete"  # User confirmed a reservation
    AWAITING_ADMIN = "awaiting_admin"  # Waiting for admin review
    ADMIN_REVIEWING = "admin_reviewing"  # Admin is reviewing
    APPROVED = "approved"  # Admin approved
    REJECTED = "rejected"  # Admin rejected
    NOTIFYING = "notifying"  # Sending email notifications
    RECORDING = "recording"  # Writing to file via MCP
    COMPLETED = "completed"  # Pipeline finished
    ERROR = "error"  # Something went wrong


class GraphState(TypedDict, total=False):
    """
    The shared state object that flows through every node in the LangGraph.

    Every node receives this state, reads what it needs, modifies its
    fields, and returns the updated state. LangGraph merges the updates.

    Fields:
        user_message: The current user input being processed
        bot_response: The chatbot's response to display to the user
        conversation_phase: Current phase in the reservation pipeline
        reservation_data: Dict of collected booking fields
        reservation_id: Database ID after saving the reservation
        admin_decision: "approve" or "reject"
        admin_notes: Optional admin notes/reason
        notification_sent: True if email was sent successfully
        mcp_recorded: True if MCP file write succeeded
        error: Error description if something failed
        history: Conversation history as list of (role, content) tuples
        is_booking_flow: True if chatbot is currently collecting reservation data
        needs_admin_input: True when graph is waiting for admin to act
        admin_input: The admin's command (e.g., "approve 1")
    """

    user_message: str
    bot_response: str
    conversation_phase: str
    reservation_data: dict
    reservation_id: int
    admin_decision: str
    admin_notes: str
    notification_sent: bool
    mcp_recorded: bool
    error: str
    history: list
    is_booking_flow: bool
    needs_admin_input: bool
    admin_input: str
