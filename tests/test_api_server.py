"""
Tests for the REST API server.

Tests cover:
1. Health check endpoint
2. Creating a reservation via POST
3. Listing reservations (with and without status filter)
4. Getting a single reservation by ID
5. Approving a reservation
6. Rejecting a reservation
7. Error handling (not found, already processed)

Uses FastAPI's TestClient which simulates HTTP requests without
needing to start a real server.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.database.sql_store import SQLStore


class TestAPIServer:
    """Tests for the FastAPI REST API endpoints."""

    def setup_method(self):
        """
        Create a fresh in-memory database for each test.
        We directly replace the server module's sql_store so all
        endpoints use our clean test DB.
        """
        self.test_store = SQLStore(database_url="sqlite:///:memory:")
        self.test_store.initialize_default_data()

        # Import server module and replace its globals with test instances
        import src.api.server as server_module

        server_module.sql_store = self.test_store
        server_module.email_service = MagicMock()
        server_module.email_service.notify_new_reservation.return_value = True

        self.client = TestClient(server_module.app)

    def _post_reservation(self):
        """Helper: submit a test reservation via API and return response."""
        return self.client.post(
            "/api/reservations",
            json={
                "first_name": "Bob",
                "last_name": "Smith",
                "email": "bob@example.com",
                "car_number": "TEST-123",
                "space_type": "standard",
                "start_datetime": "2026-05-20 08:00",
                "end_datetime": "2026-05-20 17:00",
            },
        )

    def test_health_check(self):
        """Health endpoint should return 200 with status healthy."""
        response = self.client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_create_reservation(self):
        """POST /reservations should create a new pending reservation."""
        response = self._post_reservation()
        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "Bob"
        assert data["last_name"] == "Smith"
        assert data["status"] == "pending"
        assert data["id"] is not None

    def test_list_reservations_empty(self):
        """GET /reservations should return empty list when no bookings exist."""
        response = self.client.get("/api/reservations")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_reservations_with_data(self):
        """After creating a reservation, it should appear in the list."""
        self._post_reservation()
        response = self.client.get("/api/reservations")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["car_number"] == "TEST-123"

    def test_list_reservations_filter_by_status(self):
        """Filtering by status should only return matching reservations."""
        self._post_reservation()
        # Should get 1 pending
        response = self.client.get("/api/reservations?status=pending")
        assert len(response.json()) == 1
        # Should get 0 approved
        response = self.client.get("/api/reservations?status=approved")
        assert len(response.json()) == 0

    def test_get_reservation_by_id(self):
        """GET /reservations/{id} should return the correct reservation."""
        create_resp = self._post_reservation()
        rid = create_resp.json()["id"]

        response = self.client.get(f"/api/reservations/{rid}")
        assert response.status_code == 200
        assert response.json()["car_number"] == "TEST-123"

    def test_get_reservation_not_found(self):
        """Requesting a non-existent ID should return 404."""
        response = self.client.get("/api/reservations/999")
        assert response.status_code == 404

    def test_approve_reservation(self):
        """PUT /reservations/{id}/approve should change status to approved."""
        create_resp = self._post_reservation()
        rid = create_resp.json()["id"]

        response = self.client.put(f"/api/reservations/{rid}/approve", json={"admin_notes": "Approved by test"})
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify status changed
        get_resp = self.client.get(f"/api/reservations/{rid}")
        assert get_resp.json()["status"] == "approved"

    def test_reject_reservation(self):
        """PUT /reservations/{id}/reject should change status to rejected."""
        create_resp = self._post_reservation()
        rid = create_resp.json()["id"]

        response = self.client.put(f"/api/reservations/{rid}/reject", json={"admin_notes": "No spaces left"})
        assert response.status_code == 200
        assert response.json()["success"] is True

        get_resp = self.client.get(f"/api/reservations/{rid}")
        assert get_resp.json()["status"] == "rejected"

    def test_approve_already_approved(self):
        """Approving an already-approved reservation should return 400."""
        create_resp = self._post_reservation()
        rid = create_resp.json()["id"]
        self.client.put(f"/api/reservations/{rid}/approve")

        response = self.client.put(f"/api/reservations/{rid}/approve")
        assert response.status_code == 400

    def test_reject_already_rejected(self):
        """Rejecting an already-rejected reservation should return 400."""
        create_resp = self._post_reservation()
        rid = create_resp.json()["id"]
        self.client.put(f"/api/reservations/{rid}/reject")

        response = self.client.put(f"/api/reservations/{rid}/reject")
        assert response.status_code == 400
