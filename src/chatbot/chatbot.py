"""
Main Chatbot Module - Orchestrates conversation flow.

This module provides the high-level chatbot interface that:
1. Detects user intent (asking for info vs. making a reservation)
2. Manages the reservation flow (collecting data step by step)
3. Applies guardrails before sending responses
4. Delegates to the RAG chain for knowledge retrieval

CONVERSATION STATES:
- IDLE: No active reservation, just answering questions
- COLLECTING_NAME: Waiting for user's full name
- COLLECTING_CAR: Waiting for vehicle registration number
- COLLECTING_SPACE_TYPE: Waiting for space type preference
- COLLECTING_START: Waiting for reservation start date/time
- COLLECTING_END: Waiting for reservation end date/time
- CONFIRMING: Showing summary and waiting for user confirmation

The state machine ensures we collect all required info before
escalating to the admin for approval (Stage 2).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from src.chatbot.guardrails import Guardrails
from src.chatbot.rag_chain import RAGChain
from src.database.sql_store import SQLStore
from src.database.vector_store import VectorStore
from src.notifications.email_service import EmailService
from src.utils.masking import mask_email


class ConversationState(Enum):
    """Possible states in the conversation flow."""

    IDLE = "idle"
    COLLECTING_NAME = "collecting_name"
    COLLECTING_EMAIL = "collecting_email"
    COLLECTING_CAR = "collecting_car"
    COLLECTING_SPACE_TYPE = "collecting_space_type"
    COLLECTING_START = "collecting_start"
    COLLECTING_END = "collecting_end"
    CONFIRMING = "confirming"


@dataclass
class ReservationData:
    """
    Holds the data collected during the reservation process.
    Each field is filled step-by-step as the user provides info.
    """

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    car_number: Optional[str] = None
    space_type: Optional[str] = None
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None

    def is_complete(self) -> bool:
        """Check if all required fields are filled."""
        return all(
            [
                self.first_name,
                self.last_name,
                self.email,
                self.car_number,
                self.space_type,
                self.start_datetime,
                self.end_datetime,
            ]
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "car_number": self.car_number,
            "space_type": self.space_type,
            "start_datetime": self.start_datetime,
            "end_datetime": self.end_datetime,
        }

    def summary(self) -> str:
        """Generate a human-readable summary for confirmation."""
        masked = mask_email(self.email) if self.email else "N/A"
        return (
            f"📋 Reservation Summary:\n"
            f"  • Name: {self.first_name} {self.last_name}\n"
            f"  • Email: {masked}\n"
            f"  • Vehicle: {self.car_number}\n"
            f"  • Space Type: {self.space_type}\n"
            f"  • From: {self.start_datetime}\n"
            f"  • To: {self.end_datetime}"
        )


class ParkingChatbot:
    """
    Main chatbot class that manages the full conversation.

    This is the primary interface - call chatbot.chat(message) to interact.

    It handles:
    - General Q&A (using RAG chain)
    - Reservation flow (state machine)
    - Guardrails (PII filtering)
    """

    def __init__(self):
        """Initialize all components of the chatbot."""
        # Initialize database components
        self.vector_store = VectorStore()
        self.sql_store = SQLStore()

        # Initialize the SQL database with default data
        self.sql_store.initialize_default_data()

        # Initialize the RAG chain (the "brain")
        self.rag_chain = RAGChain(
            vector_store=self.vector_store,
            sql_store=self.sql_store,
        )

        # Initialize guardrails (data protection)
        self.guardrails = Guardrails()

        # Initialize email service (for admin notifications)
        self.email_service = EmailService()

        # Conversation state tracking
        self.state = ConversationState.IDLE
        self.reservation_data = ReservationData()

    def chat(self, user_message: str) -> str:
        """
        Process a user message and return a response.

        This is the main entry point for the chatbot.

        Flow:
        1. Check guardrails on input (block if sensitive data detected)
        2. Check if we're in a reservation flow → handle state
        3. Otherwise, detect intent and respond accordingly
        4. Check guardrails on output before returning

        Args:
            user_message: The user's input text

        Returns:
            The chatbot's response string
        """
        # Step 1: Apply input guardrails
        input_check = self.guardrails.check_input(user_message)
        if input_check["blocked"]:
            return input_check["message"]

        # Step 2: Handle based on current state
        if self.state != ConversationState.IDLE:
            response = self._handle_reservation_flow(user_message)
        else:
            response = self._handle_general_query(user_message)

        # Step 3: Apply output guardrails
        filtered_response = self.guardrails.filter_output(response)

        return filtered_response

    # Marker that the LLM returns when it detects a booking intent
    BOOKING_INTENT_MARKER = "INTENT:BOOKING"

    def _handle_general_query(self, message: str) -> str:
        """
        Handle a message when we're in IDLE state.

        Uses a SINGLE LLM call for both intent detection and answering:
        - The system prompt tells the LLM to respond with "INTENT:BOOKING"
          if the user wants to CREATE a new reservation.
        - For all other messages (questions, info requests, etc.), the LLM
          answers normally using RAG context.

        This avoids the old keyword-matching problem where words like
        "reservation" in "show my reservation" would falsely trigger booking.
        """
        # Send to RAG chain — the LLM will either answer the question
        # OR return "INTENT:BOOKING" if the user wants to make a reservation
        response = self.rag_chain.ask(message)

        # Check if the LLM detected a booking intent
        if self.BOOKING_INTENT_MARKER in response.strip().upper():
            return self._start_reservation()

        # Otherwise, return the LLM's answer directly
        return response

    def _start_reservation(self) -> str:
        """Begin the reservation process by asking for the first piece of info."""
        self.state = ConversationState.COLLECTING_NAME
        self.reservation_data = ReservationData()  # Reset any previous data

        return (
            "I'd be happy to help you reserve a parking space! 🚗\n\n"
            "I'll need to collect a few details. Let's start:\n\n"
            "**Please provide your full name (first name and last name):**"
        )

    def _handle_reservation_flow(self, message: str) -> str:
        """
        Handle messages during the reservation flow (state machine).

        Each state expects specific data from the user:
        - COLLECTING_NAME → expects "FirstName LastName"
        - COLLECTING_CAR → expects license plate number
        - COLLECTING_SPACE_TYPE → expects parking type choice
        - COLLECTING_START → expects start date/time
        - COLLECTING_END → expects end date/time
        - CONFIRMING → expects yes/no
        """
        # Allow user to cancel at any point
        if message.lower() in ["cancel", "stop", "quit", "exit"]:
            self.state = ConversationState.IDLE
            self.reservation_data = ReservationData()
            return "Reservation cancelled. How else can I help you?"

        if self.state == ConversationState.COLLECTING_NAME:
            return self._collect_name(message)
        elif self.state == ConversationState.COLLECTING_EMAIL:
            return self._collect_email(message)
        elif self.state == ConversationState.COLLECTING_CAR:
            return self._collect_car(message)
        elif self.state == ConversationState.COLLECTING_SPACE_TYPE:
            return self._collect_space_type(message)
        elif self.state == ConversationState.COLLECTING_START:
            return self._collect_start_time(message)
        elif self.state == ConversationState.COLLECTING_END:
            return self._collect_end_time(message)
        elif self.state == ConversationState.CONFIRMING:
            return self._handle_confirmation(message)

        # Shouldn't reach here, but just in case
        self.state = ConversationState.IDLE
        return "Something went wrong. Let's start over. How can I help you?"

    def _collect_name(self, message: str) -> str:
        """Process the user's name input."""
        parts = message.strip().split()
        if len(parts) < 2:
            return "Please provide both your **first name** and **last name** (e.g., 'John Smith'):"

        self.reservation_data.first_name = parts[0].title()
        self.reservation_data.last_name = " ".join(parts[1:]).title()
        self.state = ConversationState.COLLECTING_EMAIL

        return (
            f"Thank you, {self.reservation_data.first_name}! ✓\n\n"
            f"**Please provide your email address** (for reservation notifications):"
        )

    def _collect_email(self, message: str) -> str:
        """Process the user's email input."""
        import re

        email = message.strip()
        # Basic email validation
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            return "That doesn't look like a valid email address. Please try again (e.g., 'john@example.com'):"

        self.reservation_data.email = email
        self.state = ConversationState.COLLECTING_CAR

        return (
            f"Email: {mask_email(email)} ✓\n\n" f"**Please provide your vehicle registration number (license plate):**"
        )

    def _collect_car(self, message: str) -> str:
        """Process the vehicle registration number."""
        car_number = message.strip().upper()
        if len(car_number) < 2:
            return "That doesn't look like a valid registration number. Please try again:"

        self.reservation_data.car_number = car_number
        self.state = ConversationState.COLLECTING_SPACE_TYPE

        return (
            f"Vehicle registered: {car_number} ✓\n\n"
            "**What type of parking space do you need?**\n"
            "  1. Standard (sedans, hatchbacks, small SUVs)\n"
            "  2. Large (large SUVs, pickup trucks, vans)\n"
            "  3. Electric Vehicle (with charging)\n"
            "  4. VIP (premium, covered spot)\n\n"
            "Please type the number or name of your choice:"
        )

    def _collect_space_type(self, message: str) -> str:
        """Process the space type selection."""
        type_mapping = {
            "1": "standard",
            "standard": "standard",
            "2": "large",
            "large": "large",
            "3": "ev",
            "ev": "ev",
            "electric": "ev",
            "electric vehicle": "ev",
            "4": "vip",
            "vip": "vip",
            "premium": "vip",
        }

        choice = message.strip().lower()
        space_type = type_mapping.get(choice)

        if not space_type:
            return (
                "I didn't understand that choice. Please select:\n"
                "  1. Standard\n  2. Large\n  3. Electric Vehicle\n  4. VIP"
            )

        self.reservation_data.space_type = space_type
        self.state = ConversationState.COLLECTING_START

        return (
            f"Space type: {space_type.upper()} ✓\n\n"
            "**When would you like to start your reservation?**\n"
            "Please provide date and time (e.g., '2026-05-10 09:00'):"
        )

    def _collect_start_time(self, message: str) -> str:
        """Process the start date/time."""
        # Basic validation - try to parse the date
        try:
            # Try common formats
            for fmt in ["%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%d"]:
                try:
                    parsed = datetime.strptime(message.strip(), fmt)
                    self.reservation_data.start_datetime = parsed.strftime("%Y-%m-%d %H:%M")
                    break
                except ValueError:
                    continue
            else:
                raise ValueError("Could not parse date")
        except (ValueError, TypeError):
            return (
                "I couldn't understand that date format. Please use:\n"
                "**YYYY-MM-DD HH:MM** (e.g., '2026-05-10 09:00')"
            )

        self.state = ConversationState.COLLECTING_END

        return (
            f"Start time: {self.reservation_data.start_datetime} ✓\n\n"
            "**When should the reservation end?**\n"
            "Please provide date and time (e.g., '2026-05-10 18:00'):"
        )

    def _collect_end_time(self, message: str) -> str:
        """Process the end date/time."""
        try:
            for fmt in ["%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%d"]:
                try:
                    parsed = datetime.strptime(message.strip(), fmt)
                    self.reservation_data.end_datetime = parsed.strftime("%Y-%m-%d %H:%M")
                    break
                except ValueError:
                    continue
            else:
                raise ValueError("Could not parse date")
        except (ValueError, TypeError):
            return (
                "I couldn't understand that date format. Please use:\n"
                "**YYYY-MM-DD HH:MM** (e.g., '2026-05-10 18:00')"
            )

        # Move to confirmation
        self.state = ConversationState.CONFIRMING

        return (
            f"End time: {self.reservation_data.end_datetime} ✓\n\n"
            f"{self.reservation_data.summary()}\n\n"
            "**Is this correct? (yes/no)**"
        )

    def _handle_confirmation(self, message: str) -> str:
        """Handle the user's confirmation of reservation details."""
        if message.lower() in ["yes", "y", "correct", "confirm", "ok"]:
            # Reservation confirmed — save to database as 'pending'
            # The admin agent (Stage 2) will pick this up for review
            self.state = ConversationState.IDLE
            reservation_info = self.reservation_data.to_dict()

            try:
                reservation_id = self.sql_store.save_reservation(reservation_info)

                # Notify admin via email about the new reservation
                try:
                    saved_reservation = self.sql_store.get_reservation_by_id(reservation_id)
                    self.email_service.notify_new_reservation(saved_reservation)
                except Exception:
                    pass  # Don't fail the reservation if email fails

                return (
                    f"✅ Your reservation request has been submitted! (ID: #{reservation_id})\n\n"
                    "An administrator has been notified and will review your request shortly.\n"
                    "You'll receive an email notification once it's approved.\n\n"
                    "Is there anything else I can help you with?"
                )
            except Exception:
                return (
                    "⚠️ There was an issue saving your reservation, but it has been noted.\n"
                    "An administrator will review your request shortly.\n\n"
                    "Is there anything else I can help you with?"
                )
        elif message.lower() in ["no", "n", "wrong", "restart"]:
            # Start over
            self.state = ConversationState.IDLE
            self.reservation_data = ReservationData()
            return (
                "No problem! Let's start over.\n"
                "Would you like to make a new reservation, or is there something else I can help with?"
            )
        else:
            return "Please answer **yes** to confirm or **no** to start over."

    def get_reservation_data(self) -> Optional[Dict[str, Any]]:
        """
        Get the current reservation data (for external processing).
        Returns None if no complete reservation exists.
        """
        if self.reservation_data.is_complete():
            return self.reservation_data.to_dict()
        return None

    def reset(self):
        """Reset the chatbot state completely."""
        self.state = ConversationState.IDLE
        self.reservation_data = ReservationData()
        self.rag_chain.clear_history()
