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

# Chatbot pipeline (lazy-initialized, per-session)
_pipeline = None
_sessions: dict[str, dict] = {}  # session_id -> pipeline_state


def _get_pipeline():
    """Lazy-init the shared LangGraph pipeline."""
    global _pipeline
    if _pipeline is None:
        from src.graph.pipeline import create_pipeline

        _pipeline = create_pipeline(sql_store=sql_store, email_service=email_service)
    return _pipeline


def _get_session_state(session_id: str) -> dict:
    """Get or create pipeline state for a session."""
    from src.graph.pipeline import create_initial_state

    if session_id not in _sessions:
        state = create_initial_state()
        state["session_id"] = session_id
        _sessions[session_id] = state
    return _sessions[session_id]


class ChatRequest(BaseModel):
    """JSON body for a chat message."""

    message: str = Field(..., json_schema_extra={"example": "What are your parking rates?"})
    session_id: Optional[str] = Field(None, json_schema_extra={"example": "abc-123"})


class ChatResponse(BaseModel):
    """JSON response from the chatbot."""

    response: str
    is_booking_flow: bool = False
    reservation_id: Optional[int] = None
    session_id: Optional[str] = None
    booking_progress: Optional[dict] = None


# ========================
# CHAT ENDPOINT
# ========================


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Send a message to the ParkSmart chatbot and receive a response.
    Supports general Q&A and the full reservation booking flow.
    Each session_id gets its own isolated conversation state.
    """
    import uuid

    from src.graph.pipeline import run_user_message

    session_id = request.session_id or str(uuid.uuid4())
    pipeline = _get_pipeline()
    state = _get_session_state(session_id)

    try:
        # Ensure session_id flows through pipeline state
        state["session_id"] = session_id
        result = run_user_message(pipeline, request.message, state)
        _sessions[session_id] = result

        # Get booking progress from the chatbot's session state
        from src.graph.nodes import _chatbot

        booking_progress = None
        if _chatbot:
            booking_progress = _chatbot.get_booking_progress(session_id)

        return ChatResponse(
            response=result.get("bot_response", "Sorry, I couldn't process your request."),
            is_booking_flow=result.get("is_booking_flow", False),
            reservation_id=result.get("reservation_id") or None,
            session_id=session_id,
            booking_progress=booking_progress,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@app.post("/api/chat/reset", response_model=StatusResponse)
def chat_reset(session_id: Optional[str] = None):
    """
    Reset conversation state for a session.
    If session_id is provided, resets that session (pipeline + chatbot).
    If not provided, creates a fresh session.
    """
    from src.graph.nodes import _chatbot

    if session_id and session_id in _sessions:
        del _sessions[session_id]
    # Also reset the chatbot's internal session state
    if session_id and _chatbot:
        _chatbot.reset_session(session_id)
    return StatusResponse(success=True, message="Chat session reset successfully")


@app.post("/api/chat/cancel-booking", response_model=ChatResponse)
def cancel_booking(session_id: Optional[str] = None):
    """Cancel an in-progress booking for the given session."""
    from src.graph.nodes import _chatbot

    if not _chatbot:
        raise HTTPException(status_code=500, detail="Chatbot not initialized")

    sid = session_id or "default"
    message = _chatbot.cancel_booking(sid)
    booking_progress = _chatbot.get_booking_progress(sid)

    # Update pipeline state if it exists
    if sid in _sessions:
        _sessions[sid]["is_booking_flow"] = False

    return ChatResponse(
        response=message,
        is_booking_flow=False,
        session_id=sid,
        booking_progress=booking_progress,
    )


@app.get("/api/chat/sessions")
def chat_sessions():
    """List active chat session IDs."""
    return {
        "sessions": [
            {"session_id": sid, "phase": state.get("conversation_phase", "unknown")} for sid, state in _sessions.items()
        ]
    }


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

    # Decrement real-time slot availability for the approved space type
    try:
        sql_store.update_availability(reservation["space_type"], delta=-1)
    except Exception as e:
        print(f"⚠ Slot availability update failed: {e}")

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
    Since the slot was never allocated (only approved bookings claim a slot),
    no availability change is needed here.
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
# PARKING AVAILABILITY & PRICING ENDPOINTS
# ========================

# Master config: parking types with INR pricing and feature metadata.
# Prices mirror initialize_default_data() in sql_store.py.
_PARKING_TYPE_META = {
    "standard": {
        "name": "Standard Parking",
        "description": "Hatchbacks, sedans & compact SUVs",
        "hourly_price": 50,
        "daily_price": 350,
        "monthly_price": 4500,
        "features": ["CCTV monitored", "Covered parking", "Elevator access"],
    },
    "large": {
        "name": "Large Vehicle",
        "description": "SUVs, pickup trucks & vans",
        "hourly_price": 80,
        "daily_price": 550,
        "monthly_price": 7000,
        "features": ["Extra-wide lanes", "High roof clearance", "Floor P4"],
    },
    "ev": {
        "name": "EV Charging",
        "description": "Level 2 + fast charging included",
        "hourly_price": 120,
        "daily_price": 800,
        "monthly_price": 9500,
        "features": ["Free charging", "Fast charge", "24/7 access"],
    },
    "vip": {
        "name": "VIP Premium",
        "description": "Closest to exit, dedicated valet",
        "hourly_price": 200,
        "daily_price": 1500,
        "monthly_price": 18000,
        "features": ["Covered premium area", "Priority access", "Valet support"],
    },
    "disabled": {
        "name": "Disabled",
        "description": "Wheelchair-accessible near elevators",
        "hourly_price": 30,
        "daily_price": 120,
        "monthly_price": 1200,
        "features": ["Wheelchair access", "Extra-wide", "Elevator priority"],
    },
    "bike": {
        "name": "Bike / 2-Wheeler",
        "description": "Bikes, scooters & electric two-wheelers",
        "hourly_price": 20,
        "daily_price": 120,
        "monthly_price": 1200,
        "features": ["Covered area", "EV bike charging", "Helmet lockers"],
    },
}


@app.get("/api/parking/availability")
def get_parking_availability():
    """
    Get live slot availability for all parking types.

    Returns counts per type with percentage and status label.
    Frontend polls this endpoint every 30 s for real-time updates.
    """
    import datetime as _dt

    summary = sql_store.get_total_availability()
    result = []
    for space_type, counts in summary.items():
        available = counts["available"]
        total = counts["total"]
        pct = round((available / total) * 100) if total else 0
        if pct >= 50:
            status = "available"
        elif pct > 0:
            status = "limited"
        else:
            status = "full"
        result.append(
            {
                "space_type": space_type,
                "available": available,
                "total": total,
                "percentage": pct,
                "status": status,
            }
        )
    return {"availability": result, "timestamp": _dt.datetime.utcnow().isoformat()}


@app.get("/api/parking/types")
def get_parking_types():
    """
    Get all parking types with INR pricing and live availability.

    Used by the frontend ParkingCards component to render interactive
    type selection with real-time slot counts.
    """
    summary = sql_store.get_total_availability()
    types = []
    for key, meta in _PARKING_TYPE_META.items():
        avail = summary.get(key, {"available": 0, "total": 0})
        available = avail["available"]
        total = avail["total"]
        pct = round((available / total) * 100) if total else 0
        types.append(
            {
                "id": key,
                **meta,
                "available_slots": available,
                "total_slots": total,
                "availability_percentage": pct,
                "is_available": available > 0,
            }
        )
    return {"types": types}


class PriceCalculateRequest(BaseModel):
    """Body for dynamic price calculation."""

    space_type: str
    start_datetime: str
    end_datetime: str


@app.post("/api/parking/calculate-price")
def calculate_price_endpoint(request: PriceCalculateRequest):
    """
    Calculate total INR cost for a booking before confirmation.

    Returns total cost, duration breakdown, and unit price.
    Called by the frontend as soon as the user selects a time range.
    """
    try:
        total, label, unit = sql_store.calculate_price(request.space_type, request.start_datetime, request.end_datetime)
        return {
            "space_type": request.space_type,
            "total_inr": total,
            "duration_label": label,
            "unit_price": unit,
            "currency": "INR",
            "formatted": f"\u20b9{total:,.0f}",
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Price calculation failed: {exc}")


@app.post("/api/parking/check-availability")
def check_availability_endpoint(space_type: str):
    """
    Check if slots are available for a specific parking type.
    Returns availability details and alternative suggestions when full.
    """
    avail = sql_store.check_availability(space_type)
    alternatives = []
    if not avail["is_available"]:
        summary = sql_store.get_total_availability()
        for alt_type, counts in summary.items():
            if alt_type != space_type and counts["available"] > 0:
                meta = _PARKING_TYPE_META.get(alt_type, {})
                alternatives.append(
                    {
                        "space_type": alt_type,
                        "name": meta.get("name", alt_type.title()),
                        "available": counts["available"],
                        "hourly_price": meta.get("hourly_price"),
                    }
                )
    avail["alternatives"] = alternatives
    return avail


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

    # Decrement availability, then notify & MCP (same as PUT approve)
    try:
        sql_store.update_availability(reservation["space_type"], delta=-1)
    except Exception as e:
        logger.warning("Slot availability update failed for #%d: %s", reservation_id, e)

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
