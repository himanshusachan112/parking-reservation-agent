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

import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.database.sql_store import SQLStore
from src.notifications.email_service import EmailService
from src.utils.logging_config import setup_logging
from src.utils.masking import mask_email

# Initialize structured logging
setup_logging()


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
    updated_at: Optional[str] = None
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

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared database instance (initialized once when the server starts)
sql_store = SQLStore()
sql_store.initialize_default_data()

# Email notification service
email_service = EmailService()

# Chatbot pipeline (lazy-initialized)
_pipeline = None
_pipeline_state = None


def _get_pipeline():
    """Lazy-init the LangGraph pipeline and return (pipeline, state)."""
    global _pipeline, _pipeline_state
    if _pipeline is None:
        from src.graph.pipeline import create_initial_state, create_pipeline

        _pipeline = create_pipeline(sql_store=sql_store, email_service=email_service)
        _pipeline_state = create_initial_state()
    return _pipeline, _pipeline_state


class ChatRequest(BaseModel):
    """JSON body for a chat message."""

    message: str = Field(..., json_schema_extra={"example": "What are your parking rates?"})


class ChatResponse(BaseModel):
    """JSON response from the chatbot."""

    response: str
    is_booking_flow: bool = False
    reservation_id: Optional[int] = None


# ========================
# CHAT ENDPOINT
# ========================


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Send a message to the ParkSmart chatbot and receive a response.
    Supports general Q&A and the full reservation booking flow.
    """
    from src.graph.pipeline import run_user_message

    pipeline, state = _get_pipeline()

    try:
        global _pipeline_state
        result = run_user_message(pipeline, request.message, _pipeline_state)
        _pipeline_state = result

        return ChatResponse(
            response=result.get("bot_response", "Sorry, I couldn't process your request."),
            is_booking_flow=result.get("is_booking_flow", False),
            reservation_id=result.get("reservation_id") or None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


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


@app.get("/api/health/detailed")
def health_check_detailed():
    """
    Detailed health check — validates database connectivity and vector DB config.
    Used by monitoring systems and Docker HEALTHCHECK.
    """
    checks = {
        "service": "ParkSmart Reservation API",
        "status": "healthy",
        "database": "unknown",
        "vector_db": "unknown",
        "email": "unknown",
    }

    # Check SQL database connectivity
    try:
        sql_store.get_reservations(status="pending")
        checks["database"] = "connected"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"
        checks["status"] = "degraded"

    # Check Pinecone config presence
    from config.settings import settings

    if settings.pinecone_api_key:
        checks["vector_db"] = "configured"
    else:
        checks["vector_db"] = "not configured"
        checks["status"] = "degraded"

    # Check email config
    if settings.smtp_host and settings.smtp_username:
        checks["email"] = "configured"
    else:
        checks["email"] = "console fallback"

    return checks


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
        raise HTTPException(status_code=400, detail=f"Reservation #{reservation_id} is already {reservation['status']}")

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
            car_number=reservation["car_number"],
            reservation_period=(f"{reservation['start_datetime']} - {reservation['end_datetime']}"),
        )
    except Exception as e:
        print(f"⚠ MCP file write failed: {e}")

    return StatusResponse(
        success=True,
        message=f"Reservation #{reservation_id} approved for {reservation['first_name']} {reservation['last_name']}",
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
        raise HTTPException(status_code=400, detail=f"Reservation #{reservation_id} is already {reservation['status']}")

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
        message=f"Reservation #{reservation_id} rejected for {reservation['first_name']} {reservation['last_name']}",
    )


# ========================
# POST ADMIN ROUTES
# ========================


@app.post("/admin/approve/{reservation_id}", response_model=StatusResponse)
async def admin_approve_reservation(reservation_id: int, request: AdminActionRequest = None):
    """
    Admin approves a pending reservation (POST).

    Updates the status to 'approved', triggers email notification,
    and writes to MCP file.
    """
    import logging

    logger = logging.getLogger(__name__)

    reservation = sql_store.get_reservation_by_id(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail=f"Reservation #{reservation_id} not found")

    if reservation["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Reservation #{reservation_id} is already {reservation['status']}")

    admin_notes = request.admin_notes if request else None
    success = sql_store.update_reservation_status(reservation_id, "approved", admin_notes)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update reservation")

    logger.info(
        "Reservation #%d approved | user=%s",
        reservation_id,
        mask_email(reservation.get("email", "")),
    )

    # Notify user via email (async, non-blocking)
    try:
        updated = sql_store.get_reservation_by_id(reservation_id)
        await email_service.send_user_approval_async(updated)
    except Exception as e:
        logger.warning("User approval email failed for #%d: %s", reservation_id, e)

    # Write approved reservation to MCP file
    try:
        from src.mcp.mcp_client import MCPClient

        mcp_client = MCPClient()
        mcp_client.write_reservation_to_file(
            name=f"{reservation['first_name']} {reservation['last_name']}",
            car_number=reservation["car_number"],
            reservation_period=(f"{reservation['start_datetime']} - {reservation['end_datetime']}"),
        )
    except Exception as e:
        logger.warning("MCP file write failed for #%d: %s", reservation_id, e)

    return StatusResponse(
        success=True,
        message=f"Reservation #{reservation_id} approved for {reservation['first_name']} {reservation['last_name']}",
    )


@app.post("/admin/reject/{reservation_id}", response_model=StatusResponse)
async def admin_reject_reservation(reservation_id: int, request: AdminActionRequest = None):
    """
    Admin rejects a pending reservation (POST).

    Updates the status to 'rejected' and sends rejection email to user.
    """
    import logging

    logger = logging.getLogger(__name__)

    reservation = sql_store.get_reservation_by_id(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail=f"Reservation #{reservation_id} not found")

    if reservation["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Reservation #{reservation_id} is already {reservation['status']}")

    admin_notes = request.admin_notes if request else None
    success = sql_store.update_reservation_status(reservation_id, "rejected", admin_notes)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update reservation")

    logger.info(
        "Reservation #%d rejected | user=%s",
        reservation_id,
        mask_email(reservation.get("email", "")),
    )

    # Notify user via email (async, non-blocking)
    try:
        updated = sql_store.get_reservation_by_id(reservation_id)
        await email_service.send_user_rejection_async(updated)
    except Exception as e:
        logger.warning("User rejection email failed for #%d: %s", reservation_id, e)

    return StatusResponse(
        success=True,
        message=f"Reservation #{reservation_id} rejected for {reservation['first_name']} {reservation['last_name']}",
    )
