"""
LangGraph Pipeline Builder — Wires Nodes Together into a State Graph.

This module creates the LangGraph StateGraph that orchestrates the
entire parking reservation pipeline:

    User Chat → Booking Complete → Admin Review → Notification → MCP Record → Done

WHAT IS A LANGGRAPH?
- LangGraph extends LangChain with graph-based orchestration
- You define NODES (processing steps) and EDGES (connections between them)
- CONDITIONAL EDGES route to different nodes based on state values
- The graph engine handles state passing, error handling, and flow control

HOW THIS GRAPH WORKS:

    ┌──────────────────┐
    │ user_interaction  │ ◄── User sends messages here
    └────────┬─────────┘
             │
     ┌───────▼────────┐
     │ is booking     │ ── No ──► END (just Q&A, return response)
     │ complete?      │
     └───────┬────────┘
             │ Yes
     ┌───────▼────────┐
     │save_reservation│ ── Confirm DB save, notify admin
     └───────┬────────┘
             │
     ┌───────▼────────┐
     │ admin_review    │ ◄── Admin inputs decision
     └───┬────────┬───┘
         │        │
      approve   reject
         │        │
     ┌───▼────┐ ┌─▼──────┐
     │ notify │ │ notify  │
     └───┬────┘ └─┬──────┘
         │        │
     ┌───▼────┐   │
     │ record │   │
     └───┬────┘   │
         │        │
     ┌───▼────────▼──┐
     │  completion    │
     └───────────────┘

USAGE:
    from src.graph.pipeline import create_pipeline, run_user_message, run_admin_decision

    # Create the pipeline
    pipeline = create_pipeline()

    # Process user messages
    state = run_user_message(pipeline, "I want to book a parking space")

    # After booking completes, run admin decision
    state = run_admin_decision(pipeline, state, "approve")
"""

from typing import Any, Dict, Optional

from langgraph.graph import END, StateGraph

from src.agents.admin_agent import AdminAgent
from src.chatbot.chatbot import ParkingChatbot
from src.database.sql_store import SQLStore
from src.graph.nodes import (
    admin_review_node,
    completion_node,
    initialize_components,
    mcp_recording_node,
    notification_node,
    save_reservation_node,
    user_interaction_node,
)
from src.graph.state import GraphState, PipelinePhase
from src.mcp.mcp_client import MCPClient
from src.notifications.email_service import EmailService

# ════════════════════════════════════════════════════
# CONDITIONAL EDGE FUNCTIONS
# ════════════════════════════════════════════════════


def after_user_interaction(state: GraphState) -> str:
    """
    Decide what happens after the user interaction node.

    - If a booking was just completed → route to save_reservation
    - Otherwise → END (return response to user, wait for next message)

    This is a CONDITIONAL EDGE — LangGraph calls this function to
    decide which node to go to next.
    """
    phase = state.get("conversation_phase", "")

    if phase == PipelinePhase.BOOKING_COMPLETE.value:
        return "save_reservation"

    # Normal Q&A or mid-booking — just return the response
    return END


def after_admin_review(state: GraphState) -> str:
    """
    Decide what happens after the admin reviews.

    - If admin approved → route to notification
    - If admin rejected → route to notification
    - If admin needs more info → END (wait for more admin input)
    """
    phase = state.get("conversation_phase", "")
    needs_input = state.get("needs_admin_input", False)

    if needs_input:
        # Admin hasn't made a decision yet — pause the graph
        return END

    if phase == PipelinePhase.APPROVED.value:
        return "notification"
    elif phase == PipelinePhase.REJECTED.value:
        return "notification"

    return END


def after_notification(state: GraphState) -> str:
    """
    Decide what happens after notification is sent.

    - If approved → route to MCP recording (write to file)
    - If rejected → route to completion (no file write needed)
    """
    decision = state.get("admin_decision", "")

    if decision == "approve":
        return "mcp_recording"

    # Rejected — skip MCP, go straight to completion
    return "completion"


# ════════════════════════════════════════════════════
# GRAPH BUILDER
# ════════════════════════════════════════════════════


def create_pipeline(
    chatbot: ParkingChatbot = None,
    sql_store: SQLStore = None,
    email_service: EmailService = None,
    mcp_client: MCPClient = None,
    admin_agent: AdminAgent = None,
) -> StateGraph:
    """
    Build and compile the LangGraph state graph.

    This function:
    1. Initializes all shared components (chatbot, DB, email, MCP)
    2. Creates the StateGraph with GraphState schema
    3. Adds all nodes (user_interaction, save, admin, notify, record, complete)
    4. Adds edges and conditional edges between nodes
    5. Compiles and returns the executable graph

    Args:
        chatbot: Optional pre-initialized ParkingChatbot
        sql_store: Optional pre-initialized SQLStore
        email_service: Optional pre-initialized EmailService
        mcp_client: Optional pre-initialized MCPClient
        admin_agent: Optional pre-initialized AdminAgent

    Returns:
        Compiled LangGraph StateGraph ready for execution
    """
    # Step 1: Initialize shared components
    initialize_components(
        chatbot=chatbot,
        sql_store=sql_store,
        email_service=email_service,
        mcp_client=mcp_client,
        admin_agent=admin_agent,
    )

    # Step 2: Create the state graph with our schema
    graph = StateGraph(GraphState)

    # Step 3: Add nodes — each node is a function that takes state, returns updates
    graph.add_node("user_interaction", user_interaction_node)
    graph.add_node("save_reservation", save_reservation_node)
    graph.add_node("admin_review", admin_review_node)
    graph.add_node("notification", notification_node)
    graph.add_node("mcp_recording", mcp_recording_node)
    graph.add_node("completion", completion_node)

    # Step 4: Set the entry point — where the graph starts
    graph.set_entry_point("user_interaction")

    # Step 5: Add edges (connections between nodes)

    # After user_interaction: go to save_reservation if booking complete, else END
    graph.add_conditional_edges(
        "user_interaction",
        after_user_interaction,
        {
            "save_reservation": "save_reservation",
            END: END,
        },
    )

    # After save_reservation: always go to admin_review
    graph.add_edge("save_reservation", "admin_review")

    # After admin_review: go to notification if decided, else END (wait for input)
    graph.add_conditional_edges(
        "admin_review",
        after_admin_review,
        {
            "notification": "notification",
            END: END,
        },
    )

    # After notification: go to mcp_recording if approved, else completion
    graph.add_conditional_edges(
        "notification",
        after_notification,
        {
            "mcp_recording": "mcp_recording",
            "completion": "completion",
        },
    )

    # After mcp_recording: always go to completion
    graph.add_edge("mcp_recording", "completion")

    # Step 6: Compile the graph
    compiled = graph.compile()

    return compiled


# ════════════════════════════════════════════════════
# HELPER FUNCTIONS FOR RUNNING THE GRAPH
# ════════════════════════════════════════════════════


def create_initial_state() -> GraphState:
    """
    Create a fresh initial state for a new conversation.

    Returns:
        GraphState with all fields set to defaults
    """
    return {
        "user_message": "",
        "bot_response": "",
        "conversation_phase": PipelinePhase.USER_INTERACTION.value,
        "reservation_data": {},
        "reservation_id": 0,
        "admin_decision": "",
        "admin_notes": "",
        "notification_sent": False,
        "mcp_recorded": False,
        "error": "",
        "history": [],
        "is_booking_flow": False,
        "needs_admin_input": False,
        "admin_input": "",
    }


def run_user_message(pipeline, user_message: str, current_state: dict = None) -> dict:
    """
    Run a user message through the pipeline.

    Takes the user's message, puts it in the state, and invokes the graph.
    The graph will:
    - Process through user_interaction node
    - If booking complete: auto-continue to save_reservation → admin_review
    - Otherwise: END and return the response

    Args:
        pipeline: The compiled LangGraph pipeline
        user_message: The user's input
        current_state: Current state to update (or creates fresh state)

    Returns:
        Updated state dict after graph execution
    """
    state = current_state or create_initial_state()
    state["user_message"] = user_message

    # Invoke the graph — it runs from entry point through all reachable nodes
    result = pipeline.invoke(state)

    return result


def run_admin_decision(pipeline, current_state: dict, admin_command: str) -> dict:
    """
    Run an admin decision through the pipeline.

    After a reservation is in AWAITING_ADMIN phase, the admin provides
    a decision. This re-invokes the graph starting from admin_review.

    We create a NEW graph invocation with the admin_input set, starting
    at the admin_review entry point.

    Args:
        pipeline: The compiled LangGraph pipeline (not used directly here)
        current_state: State from after booking was completed
        admin_command: Admin command like "approve", "reject no spaces"

    Returns:
        Updated state dict after admin processing
    """
    # We need to run the admin_review → notification → mcp → completion flow
    # Build a mini-graph for the admin decision path
    from src.graph.nodes import (
        admin_review_node,
        completion_node,
        mcp_recording_node,
        notification_node,
    )

    # Update state with admin input
    state = dict(current_state)
    state["admin_input"] = admin_command
    state["needs_admin_input"] = False

    # Run admin_review node
    admin_result = admin_review_node(state)
    state.update(admin_result)

    # Check if admin needs more input
    if state.get("needs_admin_input", False):
        return state

    # Run notification node
    notify_result = notification_node(state)
    state.update(notify_result)

    # If approved, run MCP recording
    if state.get("admin_decision") == "approve":
        mcp_result = mcp_recording_node(state)
        state.update(mcp_result)

    # Run completion node
    complete_result = completion_node(state)
    state.update(complete_result)

    return state
