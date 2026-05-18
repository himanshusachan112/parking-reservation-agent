"""
Tests for the Admin Agent module.

Tests cover:
1. Fetching pending reservations
2. Reviewing a reservation (with availability check)
3. Approving a reservation
4. Rejecting a reservation
5. Admin dashboard summary
6. Handling non-existent reservations
"""

import pytest
from unittest.mock import patch, MagicMock
from src.database.sql_store import SQLStore
from src.agents.admin_agent import AdminAgent


class TestAdminAgent:
    """Tests for the AdminAgent class."""

    def setup_method(self):
        """
        Create a fresh in-memory database and admin agent for each test.
        Using ':memory:' so each test starts with a clean slate.
        """
        self.sql_store = SQLStore(database_url="sqlite:///:memory:")
        self.sql_store.initialize_default_data()
        with patch("src.agents.admin_agent.EmailService"):
            self.agent = AdminAgent(sql_store=self.sql_store)
            self.agent.email_service = MagicMock()

    def _create_sample_reservation(self):
        """Helper: insert a sample reservation and return its ID."""
        return self.sql_store.save_reservation({
            "first_name": "Alice",
            "last_name": "Johnson",
            "email": "alice@example.com",
            "car_number": "XYZ-789",
            "space_type": "standard",
            "start_datetime": "2026-05-15 09:00",
            "end_datetime": "2026-05-15 18:00",
        })

    def test_get_pending_reservations_empty(self):
        """When no reservations exist, pending list should be empty."""
        pending = self.agent.get_pending_reservations()
        assert pending == []

    def test_get_pending_reservations_with_data(self):
        """After saving a reservation, it should appear in pending list."""
        self._create_sample_reservation()
        pending = self.agent.get_pending_reservations()
        assert len(pending) == 1
        assert pending[0]["first_name"] == "Alice"
        assert pending[0]["status"] == "pending"

    def test_review_reservation(self):
        """Review should return a formatted string with availability info."""
        rid = self._create_sample_reservation()
        review = self.agent.review_reservation(rid)
        assert "Alice Johnson" in review
        assert "XYZ-789" in review
        assert "STANDARD" in review
        assert "Availability Check" in review

    def test_review_nonexistent_reservation(self):
        """Reviewing a non-existent reservation should return error message."""
        review = self.agent.review_reservation(999)
        assert "not found" in review

    def test_approve_reservation(self):
        """Approving should change status to 'approved'."""
        rid = self._create_sample_reservation()
        result = self.agent.approve_reservation(rid, admin_notes="Looks good")
        assert "APPROVED" in result

        # Verify DB was updated
        reservation = self.sql_store.get_reservation_by_id(rid)
        assert reservation["status"] == "approved"
        assert reservation["admin_notes"] == "Looks good"
        assert reservation["approved_at"] is not None

    def test_reject_reservation(self):
        """Rejecting should change status to 'rejected' with reason."""
        rid = self._create_sample_reservation()
        result = self.agent.reject_reservation(rid, admin_notes="No spaces available")
        assert "REJECTED" in result

        reservation = self.sql_store.get_reservation_by_id(rid)
        assert reservation["status"] == "rejected"
        assert reservation["admin_notes"] == "No spaces available"

    def test_cannot_approve_already_approved(self):
        """Approving an already-approved reservation should fail."""
        rid = self._create_sample_reservation()
        self.agent.approve_reservation(rid)
        result = self.agent.approve_reservation(rid)
        assert "already" in result.lower()

    def test_cannot_reject_already_rejected(self):
        """Rejecting an already-rejected reservation should fail."""
        rid = self._create_sample_reservation()
        self.agent.reject_reservation(rid)
        result = self.agent.reject_reservation(rid)
        assert "already" in result.lower()

    def test_admin_summary(self):
        """Dashboard summary should show correct counts."""
        # Create 3 reservations: 1 approved, 1 rejected, 1 pending
        r1 = self._create_sample_reservation()
        r2 = self._create_sample_reservation()
        r3 = self._create_sample_reservation()
        self.agent.approve_reservation(r1)
        self.agent.reject_reservation(r2)

        summary = self.agent.get_admin_summary()
        assert "Pending:  1" in summary
        assert "Approved: 1" in summary
        assert "Rejected: 1" in summary
