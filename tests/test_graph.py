"""
Tests for Stage 4 — LangGraph Pipeline Orchestration.

Tests cover:
1. State schema (GraphState, PipelinePhase)
2. Individual nodes (user_interaction, save, admin, notify, MCP, completion)
3. Conditional edge routing functions
4. Full pipeline creation and compilation
5. End-to-end flow (booking → admin approve → notify → record → complete)
6. Rejection flow (booking → admin reject → notify → complete, no MCP)
7. Pipeline state management helpers

Total: 24 tests
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime

import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ════════════════════════════════════════════════════
# FIXTURES
# ════════════════════════════════════════════════════

@pytest.fixture
def mock_sql_store():
    """Create a mock SQLStore with standard responses."""
    store = MagicMock()
    store.initialize_default_data = MagicMock()
    store.get_reservation_by_id = MagicMock(return_value={
        "id": 1,
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com",
        "car_number": "TEST123",
        "space_type": "standard",
        "start_datetime": "2026-05-15 09:00",
        "end_datetime": "2026-05-15 18:00",
        "status": "pending",
        "created_at": "2026-05-10 10:00:00",
    })
    store.get_reservations = MagicMock(return_value=[])
    store.update_reservation_status = MagicMock(return_value=True)
    store.get_total_availability = MagicMock(return_value={
        "standard": {"available": 5, "total": 10},
        "large": {"available": 3, "total": 5},
        "ev": {"available": 2, "total": 4},
        "vip": {"available": 1, "total": 2},
    })
    return store


@pytest.fixture
def mock_chatbot():
    """Create a mock ParkingChatbot."""
    from src.chatbot.chatbot import ConversationState
    bot = MagicMock()
    bot.state = ConversationState.IDLE
    bot.chat = MagicMock(return_value="Hello! I'm the ParkSmart assistant.")
    return bot


@pytest.fixture
def mock_email_service():
    """Create a mock EmailService."""
    svc = MagicMock()
    svc.notify_user_status_change = MagicMock(return_value=True)
    svc.notify_new_reservation = MagicMock(return_value=True)
    return svc


@pytest.fixture
def mock_mcp_client():
    """Create a mock MCPClient."""
    client = MagicMock()
    client.write_reservation_to_file = MagicMock(return_value="✓ MCP: Written to file")
    client.is_server_available = MagicMock(return_value=True)
    return client


@pytest.fixture
def mock_admin_agent():
    """Create a mock AdminAgent."""
    agent = MagicMock()
    agent.review_reservation = MagicMock(return_value="═══ RESERVATION REVIEW ═══\nTest review")
    return agent


@pytest.fixture
def initialized_nodes(mock_chatbot, mock_sql_store, mock_email_service, mock_mcp_client, mock_admin_agent):
    """Initialize the graph nodes with mocked components."""
    from src.graph.nodes import initialize_components
    initialize_components(
        chatbot=mock_chatbot,
        sql_store=mock_sql_store,
        email_service=mock_email_service,
        mcp_client=mock_mcp_client,
        admin_agent=mock_admin_agent,
    )
    return {
        "chatbot": mock_chatbot,
        "sql_store": mock_sql_store,
        "email_service": mock_email_service,
        "mcp_client": mock_mcp_client,
        "admin_agent": mock_admin_agent,
    }


@pytest.fixture
def base_state():
    """Create a base state for testing."""
    from src.graph.state import PipelinePhase
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


# ════════════════════════════════════════════════════
# 1. STATE SCHEMA TESTS
# ════════════════════════════════════════════════════

class TestStateSchema:
    """Test the GraphState TypedDict and PipelinePhase enum."""

    def test_pipeline_phase_values(self):
        """PipelinePhase enum has all expected phases."""
        from src.graph.state import PipelinePhase
        phases = [p.value for p in PipelinePhase]
        assert "user_interaction" in phases
        assert "booking_complete" in phases
        assert "awaiting_admin" in phases
        assert "approved" in phases
        assert "rejected" in phases
        assert "notifying" in phases
        assert "recording" in phases
        assert "completed" in phases
        assert "error" in phases

    def test_pipeline_phase_count(self):
        """PipelinePhase has exactly 10 phases."""
        from src.graph.state import PipelinePhase
        assert len(PipelinePhase) == 10

    def test_graph_state_is_typed_dict(self):
        """GraphState is a TypedDict subclass."""
        from src.graph.state import GraphState
        # TypedDict creates a dict subclass
        state = GraphState(
            user_message="hello",
            bot_response="hi",
            conversation_phase="user_interaction",
        )
        assert isinstance(state, dict)
        assert state["user_message"] == "hello"

    def test_graph_state_total_false(self):
        """GraphState allows partial initialization (total=False)."""
        from src.graph.state import GraphState
        # total=False means not all keys are required
        state = GraphState(user_message="test")
        assert state["user_message"] == "test"


# ════════════════════════════════════════════════════
# 2. NODE TESTS
# ════════════════════════════════════════════════════

class TestUserInteractionNode:
    """Test the user_interaction_node."""

    def test_empty_message(self, initialized_nodes, base_state):
        """Empty message returns a prompt to type something."""
        from src.graph.nodes import user_interaction_node
        base_state["user_message"] = ""
        result = user_interaction_node(base_state)
        assert "type a message" in result["bot_response"].lower()

    def test_general_query(self, initialized_nodes, base_state, mock_chatbot):
        """General Q&A message returns chatbot response and stays in USER_INTERACTION."""
        from src.graph.nodes import user_interaction_node
        from src.graph.state import PipelinePhase

        mock_chatbot.chat.return_value = "ParkSmart is located at 123 Main St."
        base_state["user_message"] = "Where is the parking?"

        result = user_interaction_node(base_state)
        assert result["conversation_phase"] == PipelinePhase.USER_INTERACTION.value
        assert "ParkSmart" in result["bot_response"]
        mock_chatbot.chat.assert_called_with("Where is the parking?")

    def test_booking_completed(self, initialized_nodes, base_state, mock_chatbot):
        """Booking completion triggers BOOKING_COMPLETE phase."""
        from src.graph.nodes import user_interaction_node
        from src.graph.state import PipelinePhase
        from src.chatbot.chatbot import ConversationState

        # Simulate chatbot returning a booking confirmation
        mock_chatbot.chat.return_value = (
            "✅ Your reservation request has been submitted! (ID: #5)\n"
            "An administrator has been notified."
        )
        mock_chatbot.state = ConversationState.IDLE  # Back to idle after booking

        base_state["user_message"] = "yes"

        result = user_interaction_node(base_state)
        assert result["conversation_phase"] == PipelinePhase.BOOKING_COMPLETE.value
        assert result["reservation_id"] == 5
        assert result["is_booking_flow"] is False

    def test_mid_booking_flow(self, initialized_nodes, base_state, mock_chatbot):
        """Mid-booking message stays in USER_INTERACTION with is_booking_flow=True."""
        from src.graph.nodes import user_interaction_node
        from src.chatbot.chatbot import ConversationState

        mock_chatbot.chat.return_value = "Please provide your email address:"
        mock_chatbot.state = ConversationState.COLLECTING_EMAIL
        base_state["user_message"] = "John Smith"

        result = user_interaction_node(base_state)
        assert result["is_booking_flow"] is True


class TestSaveReservationNode:
    """Test the save_reservation_node."""

    def test_save_with_valid_id(self, initialized_nodes, base_state):
        """Valid reservation ID transitions to AWAITING_ADMIN."""
        from src.graph.nodes import save_reservation_node
        from src.graph.state import PipelinePhase

        base_state["reservation_id"] = 1
        result = save_reservation_node(base_state)
        assert result["conversation_phase"] == PipelinePhase.AWAITING_ADMIN.value
        assert result["needs_admin_input"] is True

    def test_save_without_id(self, initialized_nodes, base_state):
        """Missing reservation ID results in ERROR phase."""
        from src.graph.nodes import save_reservation_node
        from src.graph.state import PipelinePhase

        base_state["reservation_id"] = 0
        result = save_reservation_node(base_state)
        assert result["conversation_phase"] == PipelinePhase.ERROR.value
        assert "No reservation ID" in result["error"]


class TestAdminReviewNode:
    """Test the admin_review_node."""

    def test_review_without_input(self, initialized_nodes, base_state, mock_admin_agent):
        """No admin input returns review summary and stays waiting."""
        from src.graph.nodes import admin_review_node
        from src.graph.state import PipelinePhase

        base_state["reservation_id"] = 1
        base_state["admin_input"] = ""
        result = admin_review_node(base_state)
        assert result["needs_admin_input"] is True
        assert result["conversation_phase"] == PipelinePhase.ADMIN_REVIEWING.value
        mock_admin_agent.review_reservation.assert_called_with(1)

    def test_approve_command(self, initialized_nodes, base_state):
        """'approve' command sets admin_decision and APPROVED phase."""
        from src.graph.nodes import admin_review_node
        from src.graph.state import PipelinePhase

        base_state["reservation_id"] = 1
        base_state["admin_input"] = "approve VIP customer"
        result = admin_review_node(base_state)
        assert result["admin_decision"] == "approve"
        assert result["admin_notes"] == "VIP customer"
        assert result["conversation_phase"] == PipelinePhase.APPROVED.value
        assert result["needs_admin_input"] is False

    def test_reject_command(self, initialized_nodes, base_state):
        """'reject' command sets admin_decision and REJECTED phase."""
        from src.graph.nodes import admin_review_node
        from src.graph.state import PipelinePhase

        base_state["reservation_id"] = 1
        base_state["admin_input"] = "reject no spaces"
        result = admin_review_node(base_state)
        assert result["admin_decision"] == "reject"
        assert result["admin_notes"] == "no spaces"
        assert result["conversation_phase"] == PipelinePhase.REJECTED.value

    def test_unknown_command(self, initialized_nodes, base_state):
        """Unknown command returns help message and stays in review."""
        from src.graph.nodes import admin_review_node
        from src.graph.state import PipelinePhase

        base_state["reservation_id"] = 1
        base_state["admin_input"] = "foobar"
        result = admin_review_node(base_state)
        assert result["needs_admin_input"] is True
        assert "Unknown command" in result["bot_response"]

    def test_no_reservation(self, initialized_nodes, base_state):
        """Missing reservation ID results in ERROR."""
        from src.graph.nodes import admin_review_node
        from src.graph.state import PipelinePhase

        base_state["reservation_id"] = 0
        result = admin_review_node(base_state)
        assert result["conversation_phase"] == PipelinePhase.ERROR.value


class TestNotificationNode:
    """Test the notification_node."""

    def test_approve_notification(self, initialized_nodes, base_state, mock_sql_store, mock_email_service):
        """Approval updates DB and sends user email."""
        from src.graph.nodes import notification_node

        base_state["reservation_id"] = 1
        base_state["admin_decision"] = "approve"
        result = notification_node(base_state)

        mock_sql_store.update_reservation_status.assert_called_with(1, "approve", "")
        mock_email_service.notify_user_status_change.assert_called_once()
        assert "approved" in result["bot_response"].lower()

    def test_reject_notification(self, initialized_nodes, base_state, mock_sql_store, mock_email_service):
        """Rejection updates DB and sends user email."""
        from src.graph.nodes import notification_node

        base_state["reservation_id"] = 1
        base_state["admin_decision"] = "reject"
        base_state["admin_notes"] = "No spaces"
        result = notification_node(base_state)

        mock_sql_store.update_reservation_status.assert_called_with(1, "reject", "No spaces")
        assert "rejected" in result["bot_response"].lower()

    def test_notification_no_id(self, initialized_nodes, base_state):
        """Missing reservation ID in notification returns error."""
        from src.graph.nodes import notification_node
        base_state["reservation_id"] = 0
        result = notification_node(base_state)
        assert result["notification_sent"] is False

    def test_notification_db_failure(self, initialized_nodes, base_state, mock_sql_store):
        """DB update failure returns error phase."""
        from src.graph.nodes import notification_node
        from src.graph.state import PipelinePhase

        mock_sql_store.update_reservation_status.return_value = False
        base_state["reservation_id"] = 1
        base_state["admin_decision"] = "approve"
        result = notification_node(base_state)
        assert result["notification_sent"] is False
        assert result["conversation_phase"] == PipelinePhase.ERROR.value


class TestMCPRecordingNode:
    """Test the mcp_recording_node."""

    def test_successful_recording(self, initialized_nodes, base_state, mock_mcp_client):
        """MCP recording writes file and sets mcp_recorded=True."""
        from src.graph.nodes import mcp_recording_node

        base_state["reservation_id"] = 1
        base_state["reservation_data"] = {
            "first_name": "Test",
            "last_name": "User",
            "car_number": "TEST123",
            "start_datetime": "2026-05-15 09:00",
            "end_datetime": "2026-05-15 18:00",
        }
        result = mcp_recording_node(base_state)
        assert result["mcp_recorded"] is True
        mock_mcp_client.write_reservation_to_file.assert_called_once()

    def test_recording_failure(self, initialized_nodes, base_state, mock_mcp_client):
        """MCP recording failure sets mcp_recorded=False."""
        from src.graph.nodes import mcp_recording_node
        from src.graph.state import PipelinePhase

        mock_mcp_client.write_reservation_to_file.side_effect = Exception("Connection refused")
        base_state["reservation_id"] = 1
        base_state["reservation_data"] = {
            "first_name": "Test",
            "last_name": "User",
            "car_number": "TEST123",
            "start_datetime": "2026-05-15 09:00",
            "end_datetime": "2026-05-15 18:00",
        }
        result = mcp_recording_node(base_state)
        assert result["mcp_recorded"] is False
        assert result["conversation_phase"] == PipelinePhase.ERROR.value

    def test_recording_fetches_from_db(self, initialized_nodes, base_state, mock_sql_store):
        """If no reservation_data in state, fetches from DB."""
        from src.graph.nodes import mcp_recording_node

        base_state["reservation_id"] = 1
        base_state["reservation_data"] = {}
        result = mcp_recording_node(base_state)
        mock_sql_store.get_reservation_by_id.assert_called_with(1)
        assert result["mcp_recorded"] is True


class TestCompletionNode:
    """Test the completion_node."""

    def test_approval_complete(self, initialized_nodes, base_state):
        """Approval completion shows full summary."""
        from src.graph.nodes import completion_node
        from src.graph.state import PipelinePhase

        base_state["admin_decision"] = "approve"
        base_state["reservation_id"] = 1
        base_state["notification_sent"] = True
        base_state["mcp_recorded"] = True
        result = completion_node(base_state)
        assert result["conversation_phase"] == PipelinePhase.COMPLETED.value
        assert "APPROVED" in result["bot_response"]
        assert "Sent" in result["bot_response"]
        assert "Written" in result["bot_response"]

    def test_rejection_complete(self, initialized_nodes, base_state):
        """Rejection completion shows rejection summary."""
        from src.graph.nodes import completion_node
        from src.graph.state import PipelinePhase

        base_state["admin_decision"] = "reject"
        base_state["reservation_id"] = 1
        base_state["admin_notes"] = "No spaces"
        base_state["notification_sent"] = True
        result = completion_node(base_state)
        assert result["conversation_phase"] == PipelinePhase.COMPLETED.value
        assert "REJECTED" in result["bot_response"]
        assert "No spaces" in result["bot_response"]


# ════════════════════════════════════════════════════
# 3. CONDITIONAL EDGE TESTS
# ════════════════════════════════════════════════════

class TestConditionalEdges:
    """Test the routing functions for conditional edges."""

    def test_after_user_interaction_booking(self):
        """After user_interaction with booking → routes to save_reservation."""
        from src.graph.pipeline import after_user_interaction
        from src.graph.state import PipelinePhase

        state = {"conversation_phase": PipelinePhase.BOOKING_COMPLETE.value}
        assert after_user_interaction(state) == "save_reservation"

    def test_after_user_interaction_qa(self):
        """After user_interaction with Q&A → routes to END."""
        from src.graph.pipeline import after_user_interaction
        from src.graph.state import PipelinePhase
        from langgraph.graph import END

        state = {"conversation_phase": PipelinePhase.USER_INTERACTION.value}
        assert after_user_interaction(state) == END

    def test_after_admin_review_approved(self):
        """After admin approves → routes to notification."""
        from src.graph.pipeline import after_admin_review
        from src.graph.state import PipelinePhase

        state = {
            "conversation_phase": PipelinePhase.APPROVED.value,
            "needs_admin_input": False,
        }
        assert after_admin_review(state) == "notification"

    def test_after_admin_review_rejected(self):
        """After admin rejects → routes to notification."""
        from src.graph.pipeline import after_admin_review
        from src.graph.state import PipelinePhase

        state = {
            "conversation_phase": PipelinePhase.REJECTED.value,
            "needs_admin_input": False,
        }
        assert after_admin_review(state) == "notification"

    def test_after_admin_review_waiting(self):
        """Admin hasn't decided yet → routes to END (pause)."""
        from src.graph.pipeline import after_admin_review
        from src.graph.state import PipelinePhase
        from langgraph.graph import END

        state = {
            "conversation_phase": PipelinePhase.ADMIN_REVIEWING.value,
            "needs_admin_input": True,
        }
        assert after_admin_review(state) == END

    def test_after_notification_approved(self):
        """After notification for approval → routes to MCP recording."""
        from src.graph.pipeline import after_notification

        state = {"admin_decision": "approve"}
        assert after_notification(state) == "mcp_recording"

    def test_after_notification_rejected(self):
        """After notification for rejection → routes to completion (skip MCP)."""
        from src.graph.pipeline import after_notification

        state = {"admin_decision": "reject"}
        assert after_notification(state) == "completion"


# ════════════════════════════════════════════════════
# 4. PIPELINE CREATION TESTS
# ════════════════════════════════════════════════════

class TestPipelineCreation:
    """Test pipeline creation and compilation."""

    def test_create_pipeline(self, mock_chatbot, mock_sql_store, mock_email_service, mock_mcp_client, mock_admin_agent):
        """Pipeline creates and compiles successfully."""
        from src.graph.pipeline import create_pipeline

        pipeline = create_pipeline(
            chatbot=mock_chatbot,
            sql_store=mock_sql_store,
            email_service=mock_email_service,
            mcp_client=mock_mcp_client,
            admin_agent=mock_admin_agent,
        )
        # Compiled graph should be callable
        assert pipeline is not None
        assert hasattr(pipeline, "invoke")

    def test_create_initial_state(self):
        """create_initial_state returns a complete state dict."""
        from src.graph.pipeline import create_initial_state
        from src.graph.state import PipelinePhase

        state = create_initial_state()
        assert state["user_message"] == ""
        assert state["conversation_phase"] == PipelinePhase.USER_INTERACTION.value
        assert state["reservation_id"] == 0
        assert state["history"] == []
        assert state["is_booking_flow"] is False


# ════════════════════════════════════════════════════
# 5. HELPER FUNCTION TESTS
# ════════════════════════════════════════════════════

class TestHelperFunctions:
    """Test utility functions."""

    def test_extract_reservation_id(self):
        """Extracts reservation ID from response string."""
        from src.graph.nodes import _extract_reservation_id
        assert _extract_reservation_id("Submitted! (ID: #3)") == 3
        assert _extract_reservation_id("Reservation #12 approved") == 12
        assert _extract_reservation_id("No ID here") == 0

    def test_initialize_components(self, mock_chatbot, mock_sql_store):
        """initialize_components sets module-level variables."""
        from src.graph import nodes
        from src.graph.nodes import initialize_components

        initialize_components(
            chatbot=mock_chatbot,
            sql_store=mock_sql_store,
        )
        assert nodes._chatbot is mock_chatbot
        assert nodes._sql_store is mock_sql_store


# ════════════════════════════════════════════════════
# 6. END-TO-END FLOW TESTS
# ════════════════════════════════════════════════════

class TestEndToEndFlow:
    """Test the full pipeline flow using run_admin_decision."""

    def test_approval_flow(self, initialized_nodes, base_state, mock_sql_store, mock_mcp_client, mock_email_service):
        """Full approval flow: admin approve → notify → MCP → complete."""
        from src.graph.pipeline import run_admin_decision
        from src.graph.state import PipelinePhase

        # Set up state as if booking just completed
        base_state["reservation_id"] = 1
        base_state["conversation_phase"] = PipelinePhase.AWAITING_ADMIN.value
        base_state["reservation_data"] = {
            "first_name": "Test",
            "last_name": "User",
            "car_number": "TEST123",
            "start_datetime": "2026-05-15 09:00",
            "end_datetime": "2026-05-15 18:00",
        }

        result = run_admin_decision(None, base_state, "approve")

        # Verify all steps ran
        assert result["conversation_phase"] == PipelinePhase.COMPLETED.value
        assert result["admin_decision"] == "approve"
        mock_sql_store.update_reservation_status.assert_called_with(1, "approve", "")
        mock_email_service.notify_user_status_change.assert_called_once()
        mock_mcp_client.write_reservation_to_file.assert_called_once()
        assert "APPROVED" in result["bot_response"]

    def test_rejection_flow(self, initialized_nodes, base_state, mock_sql_store, mock_mcp_client, mock_email_service):
        """Full rejection flow: admin reject → notify → complete (no MCP)."""
        from src.graph.pipeline import run_admin_decision
        from src.graph.state import PipelinePhase

        base_state["reservation_id"] = 1
        base_state["conversation_phase"] = PipelinePhase.AWAITING_ADMIN.value

        result = run_admin_decision(None, base_state, "reject no spaces available")

        assert result["conversation_phase"] == PipelinePhase.COMPLETED.value
        assert result["admin_decision"] == "reject"
        assert "no spaces available" in result["admin_notes"]
        mock_sql_store.update_reservation_status.assert_called_with(1, "reject", "no spaces available")
        # MCP should NOT be called for rejections
        mock_mcp_client.write_reservation_to_file.assert_not_called()
        assert "REJECTED" in result["bot_response"]


# ════════════════════════════════════════════════════
# 7. RUN USER MESSAGE TEST
# ════════════════════════════════════════════════════

class TestRunUserMessage:
    """Test the run_user_message helper."""

    def test_qa_message(self, mock_chatbot, mock_sql_store, mock_email_service, mock_mcp_client, mock_admin_agent):
        """User Q&A message goes through pipeline and returns response."""
        from src.graph.pipeline import create_pipeline, run_user_message
        from src.graph.state import PipelinePhase

        mock_chatbot.chat.return_value = "ParkSmart has 200 parking spaces."

        pipeline = create_pipeline(
            chatbot=mock_chatbot,
            sql_store=mock_sql_store,
            email_service=mock_email_service,
            mcp_client=mock_mcp_client,
            admin_agent=mock_admin_agent,
        )

        result = run_user_message(pipeline, "How many spaces?")
        assert "200" in result["bot_response"]
        assert result["conversation_phase"] == PipelinePhase.USER_INTERACTION.value
