"""
Booking model – production-grade reservation lifecycle.

The `Booking` record is the authoritative source for a customer booking.
It differs from the legacy `Reservation` model in sql_store.py:
  * Stores datetimes as proper DateTime columns (not strings)
  * Tracks total_price, duration, assigned slot
  * Covers the full lifecycle: pending → approved → completed / cancelled

Legacy chatbot flow → creates a row in `reservations` (sql_store.py)
Admin approval     → creates a row here + allocates a ParkingSlot
"""

import secrets
import string
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from src.database.base import Base, TimestampMixin

# Lifecycle status values
BOOKING_PENDING = "pending"
BOOKING_APPROVED = "approved"
BOOKING_REJECTED = "rejected"
BOOKING_CANCELLED = "cancelled"
BOOKING_COMPLETED = "completed"

VALID_BOOKING_STATUSES = {
    BOOKING_PENDING,
    BOOKING_APPROVED,
    BOOKING_REJECTED,
    BOOKING_CANCELLED,
    BOOKING_COMPLETED,
}


def _generate_reference() -> str:
    """Generate a human-readable booking reference like PS-A3X8K."""
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(secrets.choice(chars) for _ in range(5))
    return f"PS-{suffix}"


class Booking(Base, TimestampMixin):
    """Production booking record – full lifecycle from request to completion."""

    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Unique human-readable reference shown to the customer
    booking_reference = Column(
        String(20),
        nullable=False,
        default=_generate_reference,
        unique=True,
    )

    # Customer details
    user_name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=True)
    vehicle_number = Column(String(50), nullable=False)
    vehicle_type = Column(String(50), nullable=True)  # "car", "suv", "ev", "bike"

    # Parking type FK
    parking_type_id = Column(
        Integer,
        ForeignKey("parking_types.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Assigned slot (NULL until approved and a slot is allocated)
    assigned_slot_id = Column(
        Integer,
        ForeignKey("parking_slots.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Booking window – stored as proper UTC datetimes
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)

    # Financials – calculated and locked at approval time (INR only)
    total_price = Column(Numeric(10, 2), nullable=True)
    booking_duration_hours = Column(Float, nullable=True)

    # Lifecycle
    status = Column(String(20), default=BOOKING_PENDING, nullable=False)
    admin_notes = Column(Text, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    # Link back to the legacy chatbot reservation (optional bridge)
    legacy_reservation_id = Column(Integer, nullable=True)

    # Relationships
    parking_type = relationship("ParkingType", back_populates="bookings")
    assigned_slot = relationship(
        "ParkingSlot",
        foreign_keys=[assigned_slot_id],
        uselist=False,
    )
    admin_actions = relationship(
        "AdminAction",
        back_populates="booking",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Booking ref={self.booking_reference!r} "
            f"user={self.user_name!r} status={self.status!r}>"
        )

    @property
    def duration_hours(self) -> float:
        """Computed duration in hours (positive only)."""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return max(delta.total_seconds() / 3600, 1.0)
        return self.booking_duration_hours or 0.0
