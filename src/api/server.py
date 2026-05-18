"""
REST API Server - Communication Bridge Between User Chatbot and Admin.

This FastAPI server provides endpoints for:
1. Submitting reservation requests (called by the user chatbot)
2. Listing pending reservations (called by the admin agent)
3. Approving/rejecting reservations (called by the admin agent)

WHY A REST API?
The Stage 2 task says: "Chat bot should be able to send a reservation request
to administrator and get confirm/refuse response from him (e.g. via email
server, messenger, rest api)."

We use REST API because:
- Decouples the user chatbot from the admin agent (they don't need to run together)
- Standard HTTP interface (can be called from CLI, web UI, or other agents)
- Easy to test and debug
- Can be extended with email/webhook notifications

ENDPOINTS:
    POST   /api/reservations              - Submit a new reservation
    GET    /api/reservations              - List reservations (filter by ?status=pending)
    GET    /api/reservations/{id}         - Get a specific reservation
    PUT    /api/reservations/{id}/approve - Admin approves a reservation
    PUT    /api/reservations/{id}/reject  - Admin rejects a reservation
    GET    /api/health                    - Health check

HOW TO RUN:
    python -m uvicorn src.api.server:app --reload --port 8000
    Then visit http://localhost:8000/docs for interactive Swagger UI
"""

import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Optional
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from src.database.sql_store import SQLStore
from src.notifications.email_service import EmailService


# ========================
# PYDANTIC REQUEST/RESPONSE MODELS
# ========================
# These define the shape of JSON data sent/received by the API.
# FastAPI uses them for validation AND auto-generated Swagger docs.

class ReservationRequest(BaseModel):
    """JSON body for creating a new reservation (sent by chatbot)."""
    first_name: str = Field(..., json_schema_extra={"example": "John"})
    last_name: str = Field(..., json_schema_extra={"example": "Smith"})
    email: Optional[str] = Field(None, json_schema_extra={"example": "john@example.com"})
    car_number: str = Field(..., json_schema_extra={"example": "ABC-1234"})
    space_type: str = Field(..., json_schema_extra={"example": "standard"})
    start_datetime: str = Field(..., json_schema_extra={"example": "2026-05-10 09:00"})
    end_datetime: str = Field(..., json_schema_extra={"example": "2026-05-10 18:00"})


class ReservationResponse(BaseModel):
    """JSON response when returning reservation data."""
    id: int
    first_name: str
    last_name: str
    email: Optional[str] = None
    car_number: str
    space_type: str
    start_datetime: str
    end_datetime: str
    status: str
    admin_notes: Optional[str] = None
    created_at: Optional[str] = None
    approved_at: Optional[str] = None


class AdminActionRequest(BaseModel):
    """JSON body for admin approve/reject action."""
    admin_notes: Optional[str] = Field(None, json_schema_extra={"example": "Approved - VIP customer"})


class StatusResponse(BaseModel):
    """Generic status response."""
    success: bool
    message: str


# ========================
# FASTAPI APPLICATION
# ========================

app = FastAPI(
    title="ParkSmart Reservation API",
    description=(
        "REST API for the ParkSmart Parking Reservation System.\n\n"
        "Used for communication between the user-facing chatbot and "
        "the admin agent for reservation approval."
    ),
    version="1.0.0",
)

# Shared database instance (initialized once when the server starts)
sql_store = SQLStore()
sql_store.initialize_default_data()

# Email notification service
email_service = EmailService()


# ========================
# API ENDPOINTS
# ========================

@app.get("/api/health")
def health_check():
    """
    Health check endpoint.
    Returns OK if the server is running and DB is accessible.
    """
    return {"status": "healthy", "service": "ParkSmart Reservation API"}


@app.post("/api/reservations", response_model=ReservationResponse, status_code=201)
def create_reservation(request: ReservationRequest):
    """
    Submit a new reservation request.

    Called by the user-facing chatbot when a user confirms their booking.
    The reservation is saved with status='pending' for admin review.

    Also sends an email notification to the admin (if configured).
    """
    reservation_data = request.model_dump()

    try:
        reservation_id = sql_store.save_reservation(reservation_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save reservation: {str(e)}")

    # Fetch the saved reservation to return it
    reservation = sql_store.get_reservation_by_id(reservation_id)

    # Notify admin via email (non-blocking — doesn't fail if email fails)
    try:
        email_service.notify_new_reservation(reservation)
    except Exception as e:
        print(f"⚠ Email notification failed: {e}")

    return reservation


@app.get("/api/reservations", response_model=list[ReservationResponse])
def list_reservations(status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected")):
    """
    List all reservations, optionally filtered by status.

    The admin agent calls this to see pending reservations that need review.
    """
    valid_statuses = ["pending", "approved", "rejected", None]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: pending, approved, rejected")

    reservations = sql_store.get_reservations(status=status)
    return reservations


@app.get("/api/reservations/{reservation_id}", response_model=ReservationResponse)
def get_reservation(reservation_id: int):
    """
    Get details of a specific reservation by ID.
    """
    reservation = sql_store.get_reservation_by_id(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail=f"Reservation #{reservation_id} not found")
    return reservation


@app.put("/api/reservations/{reservation_id}/approve", response_model=StatusResponse)
def approve_reservation(reservation_id: int, request: AdminActionRequest = None):
    """
    Admin approves a pending reservation.

    Updates the status to 'approved' and records the timestamp.
    Optionally includes admin notes.
    """
    # Check if reservation exists
    reservation = sql_store.get_reservation_by_id(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail=f"Reservation #{reservation_id} not found")

    if reservation["status"] != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Reservation #{reservation_id} is already {reservation['status']}"
        )

    admin_notes = request.admin_notes if request else None
    success = sql_store.update_reservation_status(reservation_id, "approved", admin_notes)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update reservation")

    # Notify the user via email about the approval
    try:
        updated = sql_store.get_reservation_by_id(reservation_id)
        email_service.notify_user_status_change(updated)
    except Exception as e:
        print(f"⚠ User notification failed: {e}")

    # Write approved reservation to file via MCP server (Stage 3)
    try:
        from src.mcp.mcp_client import MCPClient
        mcp_client = MCPClient()
        mcp_client.write_reservation_to_file(
            name=f"{reservation['first_name']} {reservation['last_name']}",
            car_number=reservation['car_number'],
            reservation_period=(
                f"{reservation['start_datetime']} - {reservation['end_datetime']}"
            ),
        )
    except Exception as e:
        print(f"⚠ MCP file write failed: {e}")

    return StatusResponse(
        success=True,
        message=f"Reservation #{reservation_id} approved for {reservation['first_name']} {reservation['last_name']}"
    )


@app.put("/api/reservations/{reservation_id}/reject", response_model=StatusResponse)
def reject_reservation(reservation_id: int, request: AdminActionRequest = None):
    """
    Admin rejects a pending reservation.

    Updates the status to 'rejected' with optional reason.
    """
    reservation = sql_store.get_reservation_by_id(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail=f"Reservation #{reservation_id} not found")

    if reservation["status"] != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Reservation #{reservation_id} is already {reservation['status']}"
        )

    admin_notes = request.admin_notes if request else None
    success = sql_store.update_reservation_status(reservation_id, "rejected", admin_notes)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update reservation")

    # Notify the user via email about the rejection
    try:
        updated = sql_store.get_reservation_by_id(reservation_id)
        email_service.notify_user_status_change(updated)
    except Exception as e:
        print(f"⚠ User notification failed: {e}")

    return StatusResponse(
        success=True,
        message=f"Reservation #{reservation_id} rejected for {reservation['first_name']} {reservation['last_name']}"
    )
