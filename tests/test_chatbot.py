"""
Tests for the main Chatbot module.

These tests verify that:
1. The chatbot handles general queries
2. The reservation flow works correctly (state machine)
3. Cancellation during reservation works
4. Invalid inputs are handled gracefully

Uses mocks to avoid actual LLM API calls during testing.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.chatbot.chatbot import ConversationState, ParkingChatbot, ReservationData


class TestReservationData:
    """Tests for the ReservationData dataclass."""

    def test_incomplete_reservation(self):
        """Test that incomplete data is correctly identified."""
        data = ReservationData(first_name="John")
        assert data.is_complete() is False

    def test_complete_reservation(self):
        """Test that complete data is correctly identified."""
        data = ReservationData(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            car_number="ABC-1234",
            space_type="standard",
            start_datetime="2026-05-10 09:00",
            end_datetime="2026-05-10 18:00",
        )
        assert data.is_complete() is True

    def test_to_dict(self):
        """Test dictionary conversion."""
        data = ReservationData(first_name="John", last_name="Doe")
        result = data.to_dict()
        assert result["first_name"] == "John"
        assert result["last_name"] == "Doe"
        assert result["car_number"] is None

    def test_summary_format(self):
        """Test that summary generates readable text."""
        data = ReservationData(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            car_number="ABC-1234",
            space_type="standard",
            start_datetime="2026-05-10 09:00",
            end_datetime="2026-05-10 18:00",
        )
        summary = data.summary()
        assert "John Doe" in summary
        assert "ABC-1234" in summary
        assert "standard" in summary
        assert "jo***@example.com" in summary


class TestParkingChatbot:
    """Tests for the ParkingChatbot class."""

    def setup_method(self):
        """Set up chatbot with mocked dependencies."""
        with (
            patch("src.chatbot.chatbot.VectorStore") as mock_vector,
            patch("src.chatbot.chatbot.SQLStore") as mock_sql,
            patch("src.chatbot.chatbot.RAGChain") as mock_rag,
            patch("src.chatbot.chatbot.Guardrails") as mock_guardrails,
        ):

            # Configure guardrails mock
            mock_guardrails_instance = MagicMock()
            mock_guardrails_instance.check_input.return_value = {"blocked": False, "reason": None, "message": None}
            mock_guardrails_instance.filter_output.side_effect = lambda x: x
            mock_guardrails.return_value = mock_guardrails_instance

            # Configure SQL mock
            mock_sql_instance = MagicMock()
            mock_sql.return_value = mock_sql_instance

            # Configure vector store mock
            mock_vector_instance = MagicMock()
            mock_vector.return_value = mock_vector_instance

            # Configure RAG chain mock
            mock_rag_instance = MagicMock()
            mock_rag_instance.ask.return_value = "The parking is located at 123 Main Street."
            mock_rag.return_value = mock_rag_instance

            self.chatbot = ParkingChatbot()

    def test_reservation_intent_triggers_flow(self):
        """Test that LLM-detected booking intent starts the reservation flow."""
        # Mock the RAG chain to return the booking intent marker
        self.chatbot.rag_chain.ask.return_value = "INTENT:BOOKING"
        response = self.chatbot.chat("I want to reserve a parking spot")
        assert self.chatbot.state == ConversationState.COLLECTING_NAME
        assert "name" in response.lower()

    def test_reservation_flow_collects_name(self):
        """Test name collection in reservation flow."""
        self.chatbot.rag_chain.ask.return_value = "INTENT:BOOKING"
        self.chatbot.chat("I want to book a spot")
        response = self.chatbot.chat("John Doe")

        assert self.chatbot.reservation_data.first_name == "John"
        assert self.chatbot.reservation_data.last_name == "Doe"
        assert self.chatbot.state == ConversationState.COLLECTING_EMAIL

    def test_reservation_flow_collects_car(self):
        """Test car number collection."""
        self.chatbot.rag_chain.ask.return_value = "INTENT:BOOKING"
        self.chatbot.chat("reserve")
        self.chatbot.chat("John Doe")
        self.chatbot.chat("john@example.com")
        response = self.chatbot.chat("ABC-1234")

        assert self.chatbot.reservation_data.car_number == "ABC-1234"
        assert self.chatbot.state == ConversationState.COLLECTING_SPACE_TYPE

    def test_reservation_flow_collects_space_type(self):
        """Test space type selection."""
        self.chatbot.rag_chain.ask.return_value = "INTENT:BOOKING"
        self.chatbot.chat("book a spot")
        self.chatbot.chat("John Doe")
        self.chatbot.chat("john@example.com")
        self.chatbot.chat("ABC-1234")
        response = self.chatbot.chat("1")  # Standard

        assert self.chatbot.reservation_data.space_type == "standard"
        assert self.chatbot.state == ConversationState.COLLECTING_START

    def test_reservation_cancel(self):
        """Test that user can cancel reservation at any point."""
        self.chatbot.rag_chain.ask.return_value = "INTENT:BOOKING"
        self.chatbot.chat("reserve")
        assert self.chatbot.state == ConversationState.COLLECTING_NAME

        response = self.chatbot.chat("cancel")
        assert self.chatbot.state == ConversationState.IDLE
        assert "cancelled" in response.lower()

    def test_invalid_name_reprompts(self):
        """Test that single-word name is rejected."""
        self.chatbot.rag_chain.ask.return_value = "INTENT:BOOKING"
        self.chatbot.chat("reserve")
        response = self.chatbot.chat("John")  # Only first name

        # Should still be collecting name
        assert self.chatbot.state == ConversationState.COLLECTING_NAME
        assert "first name" in response.lower() or "last name" in response.lower()

    def test_invalid_space_type_reprompts(self):
        """Test that invalid space type choice is rejected."""
        self.chatbot.rag_chain.ask.return_value = "INTENT:BOOKING"
        self.chatbot.chat("reserve")
        self.chatbot.chat("John Doe")
        self.chatbot.chat("john@example.com")
        self.chatbot.chat("ABC-1234")
        response = self.chatbot.chat("invalid_choice")

        # Should still be collecting space type
        assert self.chatbot.state == ConversationState.COLLECTING_SPACE_TYPE

    def test_general_query_uses_rag(self):
        """Test that non-reservation queries go to RAG chain."""
        response = self.chatbot.chat("Where is the parking?")
        assert self.chatbot.state == ConversationState.IDLE
        # RAG chain mock returns "123 Main Street"
        assert "123 Main Street" in response
