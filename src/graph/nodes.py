"""
LangGraph Nodes — Individual Processing Steps in the Pipeline.

Each node is a function that:
1. Receives the full GraphState
2. Reads the fields it needs
3. Performs its task (chatbot reply, admin review, email, MCP write)
4. Returns a dict with ONLY the fields it changed

LangGraph merges the returned dict into the full state automatically.

NODE MAP:
┌─────────────────────┐
│  user_interaction    │ ← Chatbot handles Q&A + reservation collection
└─────────┬───────────┘
          │ (booking confirmed)
┌─────────▼───────────┐
│  save_reservation    │ ← Saves to DB, sends admin email
└─────────┬───────────┘
          │
┌─────────▼───────────┐
│  admin_review        │ ← Admin reviews + decides (human-in-the-loop)
└─────────┬───────────┘
          │
    ┌─────┴──────┐
    │            │
 approve      reject
    │            │
┌───▼──┐    ┌───▼──────┐
│notify│    │notify_rej │
└───┬──┘    └───┬──────┘
    │           │
┌───▼──┐       │
│record│       │
└───┬──┘       │
    │           │
┌───▼───────────▼─┐
│   completed      │
└──────────────────┘
"""

from typing import Any, Dict

from src.agents.admin_agent import AdminAgent
from src.chatbot.chatbot import ConversationState, ParkingChatbot
from src.database.sql_store import SQLStore
from src.graph.state import GraphState, PipelinePhase
from src.mcp.mcp_client import MCPClient
from src.notifications.email_service import EmailService

# ════════════════════════════════════════════════════
# SHARED COMPONENTS (initialized once, reused by nodes)
# ════════════════════════════════════════════════════

# These are module-level singletons so all nodes share the same
# database, chatbot, and services. Initialized by create_graph().

_chatbot: ParkingChatbot = None
_sql_store: SQLStore = None
_email_service: EmailService = None
_mcp_client: MCPClient = None
_admin_agent: AdminAgent = None


def initialize_components(
    chatbot: ParkingChatbot = None,
    sql_store: SQLStore = None,
    email_service: EmailService = None,
    mcp_client: MCPClient = None,
    admin_agent: AdminAgent = None,
):
    """
    Initialize shared components used by all graph nodes.

    This is called once when creating the graph. All nodes then
    use these same instances — same DB, same chatbot state, etc.

    Args:
        chatbot: ParkingChatbot instance (creates new if None)
        sql_store: SQLStore instance (creates new if None)
        email_service: EmailService instance (creates new if None)
        mcp_client: MCPClient instance (creates new if None)
        admin_agent: AdminAgent instance (creates new if None)
    """
    import logging
    _log = logging.getLogger(__name__)
    global _chatbot, _sql_store, _email_service, _mcp_client, _admin_agent

    # ── Stage: SQL store ────────────────────────────────────────────────────
    _log.info("[PIPELINE] SQL INIT START")
    _sql_store = sql_store or SQLStore()
    _sql_store.initialize_default_data()
    _log.info("[PIPELINE] SQL INIT DONE")

    # ── Stage: Chatbot ──────────────────────────────────────────────────────
    # When called from _init_pipeline_background(), a pre-built chatbot in
    # SQL-only mode is passed here.  Vector store is loaded lazily after
    # the pipeline is marked ready, then hot-swapped via RAGChain.set_vector_store().
    if chatbot is not None:
        _log.info("[PIPELINE] CHATBOT INIT DONE (pre-built SQL-only mode — RAG upgrades lazily)")
        _chatbot = chatbot
    else:
        _log.info("[PIPELINE] CHATBOT INIT START")
        _chatbot = ParkingChatbot()
        _log.info("[PIPELINE] CHATBOT INIT DONE")

    # ── Stage: Email service ────────────────────────────────────────────────
    _log.info("[PIPELINE] EMAIL SERVICE INIT START")
    _email_service = email_service or EmailService()
    _log.info("[PIPELINE] EMAIL SERVICE INIT DONE")

    # ── Stage: MCP client ───────────────────────────────────────────────────
    _log.info("[PIPELINE] MCP CLIENT INIT START")
    _mcp_client = mcp_client or MCPClient()
    _log.info("[PIPELINE] MCP CLIENT INIT DONE")

    # ── Stage: Admin agent (LLM + tools) ────────────────────────────────────
    _log.info("[PIPELINE] AGENTS INIT START")
    _admin_agent = admin_agent or AdminAgent(sql_store=_sql_store)
    _log.info("[PIPELINE] AGENTS DONE")


# ════════════════════════════════════════════════════
# NODE 1: USER INTERACTION
# ════════════════════════════════════════════════════


def user_interaction_node(state: GraphState) -> Dict[str, Any]:
    """
    Handle user messages through the chatbot.

    This node:
    1. Takes the user's message from the state
    2. Passes it to the ParkingChatbot (which has its own state machine)
    3. Checks if a booking was just completed (confirmed)
    4. Returns the bot response and updated phase

    The chatbot internally handles:
    - General Q&A (RAG chain)
    - Intent detection (INTENT:BOOKING)
    - Reservation flow (state machine: name → email → car → type → dates → confirm)

    Returns:
        Updated state with bot_response and conversation_phase
    """
    user_message = state.get("user_message", "")
    session_id = state.get("session_id")

    if not user_message:
        return {
            "bot_response": "Please type a message to get started.",
            "conversation_phase": PipelinePhase.USER_INTERACTION.value,
        }

    # Pass message to the chatbot with session isolation
    response = _chatbot.chat(user_message, session_id=session_id)

    # Check if the chatbot just completed a booking (state went back to IDLE
    # AND the response contains a reservation ID)
    is_booking = _chatbot.get_session_state(session_id) != ConversationState.IDLE.value
    booking_just_completed = "reservation request has been submitted" in response.lower() or "id: #" in response.lower()

    if booking_just_completed:
        # Extract reservation ID from response (format: "ID: #N")
        reservation_id = _extract_reservation_id(response)

        # Get the reservation data from DB
        reservation = None
        if reservation_id:
            reservation = _sql_store.get_reservation_by_id(reservation_id)

        return {
            "bot_response": response,
            "conversation_phase": PipelinePhase.BOOKING_COMPLETE.value,
            "reservation_id": reservation_id or 0,
            "reservation_data": reservation or {},
            "is_booking_flow": False,
            "history": state.get("history", [])
            + [
                ("user", user_message),
                ("bot", response),
            ],
        }

    # Normal conversation (Q&A or mid-booking flow)
    return {
        "bot_response": response,
        "conversation_phase": PipelinePhase.USER_INTERACTION.value,
        "is_booking_flow": is_booking,
        "history": state.get("history", [])
        + [
            ("user", user_message),
            ("bot", response),
        ],
    }


def _extract_reservation_id(response: str) -> int:
    """
    Extract reservation ID from chatbot response.

    The chatbot returns: "Your reservation request has been submitted! (ID: #3)"
    We parse out the number after "#".

    Args:
        response: The chatbot's response string

    Returns:
        The reservation ID as int, or 0 if not found
    """
    import re

    match = re.search(r"#(\d+)", response)
    if match:
        return int(match.group(1))
    return 0


# ════════════════════════════════════════════════════
# NODE 2: SAVE & NOTIFY ADMIN
# ════════════════════════════════════════════════════


def save_reservation_node(state: GraphState) -> Dict[str, Any]:
    """
    After booking is complete, notify admin and transition to awaiting state.

    The reservation was already saved to DB by the chatbot's _handle_confirmation().
    This node:
    1. Sends admin email notification (already done by chatbot, but we ensure it)
    2. Transitions the pipeline to AWAITING_ADMIN phase

    Returns:
        Updated state with conversation_phase = AWAITING_ADMIN
    """
    reservation_id = state.get("reservation_id", 0)

    if not reservation_id:
        return {
            "conversation_phase": PipelinePhase.ERROR.value,
            "error": "No reservation ID found after booking.",
        }

    # The chatbot already saved to DB and notified admin.
    # We just update the phase to indicate we're waiting for admin action.
    return {
        "conversation_phase": PipelinePhase.AWAITING_ADMIN.value,
        "bot_response": state.get("bot_response", ""),
        "needs_admin_input": True,
    }


# ════════════════════════════════════════════════════
# NODE 3: ADMIN REVIEW (Human-in-the-Loop)
# ════════════════════════════════════════════════════


def admin_review_node(state: GraphState) -> Dict[str, Any]:
    """
    Admin reviews the reservation and makes a decision.

    This is the HUMAN-IN-THE-LOOP node. The graph pauses here
    and waits for the admin to provide input via admin_input field.

    The admin_input can be:
    - "approve" or "approve [notes]" → approve the reservation
    - "reject" or "reject [reason]" → reject the reservation
    - "review" → get a detailed review with availability check

    Returns:
        Updated state with admin_decision and conversation_phase
    """
    reservation_id = state.get("reservation_id", 0)
    admin_input = state.get("admin_input", "").strip()
    admin_input_lower = admin_input.lower()

    if not reservation_id:
        return {
            "conversation_phase": PipelinePhase.ERROR.value,
            "error": "No reservation to review.",
        }

    if not admin_input:
        # Generate review summary for the admin
        review = _admin_agent.review_reservation(reservation_id)
        return {
            "bot_response": review,
            "conversation_phase": PipelinePhase.ADMIN_REVIEWING.value,
            "needs_admin_input": True,
        }

    # Parse admin command
    if admin_input_lower.startswith("approve"):
        notes = admin_input[len("approve") :].strip() or None
        return {
            "admin_decision": "approve",
            "admin_notes": notes or "",
            "conversation_phase": PipelinePhase.APPROVED.value,
            "needs_admin_input": False,
        }
    elif admin_input_lower.startswith("reject"):
        notes = admin_input[len("reject") :].strip() or "No reason provided"
        return {
            "admin_decision": "reject",
            "admin_notes": notes,
            "conversation_phase": PipelinePhase.REJECTED.value,
            "needs_admin_input": False,
        }
    elif admin_input_lower.startswith("review"):
        review = _admin_agent.review_reservation(reservation_id)
        return {
            "bot_response": review,
            "conversation_phase": PipelinePhase.ADMIN_REVIEWING.value,
            "needs_admin_input": True,
        }
    else:
        return {
            "bot_response": "Unknown command. Use 'approve', 'reject [reason]', or 'review'.",
            "conversation_phase": PipelinePhase.ADMIN_REVIEWING.value,
            "needs_admin_input": True,
        }


# ════════════════════════════════════════════════════
# NODE 4: NOTIFICATION (Email)
# ════════════════════════════════════════════════════


def notification_node(state: GraphState) -> Dict[str, Any]:
    """
    Send email notifications based on admin decision.

    For APPROVED reservations:
    - Updates DB status to 'approved'
    - Sends email to the user about approval

    For REJECTED reservations:
    - Updates DB status to 'rejected'
    - Sends email to the user about rejection

    Returns:
        Updated state with notification_sent flag
    """
    reservation_id = state.get("reservation_id", 0)
    decision = state.get("admin_decision", "")
    notes = state.get("admin_notes", "")

    if not reservation_id:
        return {
            "notification_sent": False,
            "error": "No reservation ID for notification.",
        }

    # Update the reservation status in the database
    success = _sql_store.update_reservation_status(reservation_id, decision, notes)

    if not success:
        return {
            "notification_sent": False,
            "error": f"Failed to update reservation #{reservation_id} to {decision}.",
            "conversation_phase": PipelinePhase.ERROR.value,
        }

    # Send email to the user
    email_sent = False
    try:
        updated_reservation = _sql_store.get_reservation_by_id(reservation_id)
        if updated_reservation:
            email_sent = _email_service.notify_user_status_change(updated_reservation)
    except Exception as e:
        print(f"⚠ Email notification failed: {e}")

    phase = PipelinePhase.NOTIFYING.value
    if decision == "approve":
        result_msg = f"✅ Reservation #{reservation_id} approved. User notified."
    else:
        result_msg = f"🚫 Reservation #{reservation_id} rejected. User notified."

    return {
        "notification_sent": email_sent,
        "bot_response": result_msg,
        "conversation_phase": phase,
    }


# ════════════════════════════════════════════════════
# NODE 5: MCP RECORDING (File Write)
# ════════════════════════════════════════════════════


def mcp_recording_node(state: GraphState) -> Dict[str, Any]:
    """
    Write approved reservation to file via MCP server.

    This node only runs for APPROVED reservations. It calls the
    MCP client to write the reservation record to
    data/approved_reservations.txt (via MCP server or fallback).

    Returns:
        Updated state with mcp_recorded flag
    """
    reservation_id = state.get("reservation_id", 0)
    reservation = state.get("reservation_data", {})

    if not reservation:
        # Fetch from DB if not in state
        reservation = _sql_store.get_reservation_by_id(reservation_id)

    if not reservation:
        return {
            "mcp_recorded": False,
            "error": f"Reservation #{reservation_id} not found for MCP recording.",
        }

    # Write to file via MCP
    try:
        name = f"{reservation.get('first_name', '')} {reservation.get('last_name', '')}"
        car_number = reservation.get("car_number", "")
        period = f"{reservation.get('start_datetime', '')} - {reservation.get('end_datetime', '')}"

        result = _mcp_client.write_reservation_to_file(
            name=name,
            car_number=car_number,
            reservation_period=period,
        )

        return {
            "mcp_recorded": True,
            "bot_response": f"✅ Reservation #{reservation_id} approved, notified, and recorded.\n  {result}",
            "conversation_phase": PipelinePhase.RECORDING.value,
        }
    except Exception as e:
        return {
            "mcp_recorded": False,
            "error": f"MCP recording failed: {e}",
            "conversation_phase": PipelinePhase.ERROR.value,
        }


# ════════════════════════════════════════════════════
# NODE 6: COMPLETION
# ════════════════════════════════════════════════════


def completion_node(state: GraphState) -> Dict[str, Any]:
    """
    Final node — marks the pipeline as completed.

    Generates a final summary message based on what happened:
    - If approved: "Reservation approved, user notified, file recorded"
    - If rejected: "Reservation rejected, user notified"

    Returns:
        Updated state with conversation_phase = COMPLETED
    """
    decision = state.get("admin_decision", "")
    reservation_id = state.get("reservation_id", 0)
    mcp_recorded = state.get("mcp_recorded", False)
    notification_sent = state.get("notification_sent", False)

    if decision == "approve":
        summary = (
            f"═══ PIPELINE COMPLETE ═══\n"
            f"Reservation #{reservation_id}: APPROVED ✅\n"
            f"  Email notification: {'✅ Sent' if notification_sent else '⚠ Failed'}\n"
            f"  MCP file record: {'✅ Written' if mcp_recorded else '⚠ Failed'}\n"
            f"═════════════════════════"
        )
    elif decision == "reject":
        summary = (
            f"═══ PIPELINE COMPLETE ═══\n"
            f"Reservation #{reservation_id}: REJECTED 🚫\n"
            f"  Reason: {state.get('admin_notes', 'No reason')}\n"
            f"  Email notification: {'✅ Sent' if notification_sent else '⚠ Failed'}\n"
            f"═════════════════════════"
        )
    else:
        summary = (
            f"═══ PIPELINE COMPLETE ═══\n" f"Reservation #{reservation_id}: Processed\n" f"═════════════════════════"
        )

    return {
        "bot_response": summary,
        "conversation_phase": PipelinePhase.COMPLETED.value,
    }
