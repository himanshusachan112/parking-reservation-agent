"""
ParkingSlot model – individual physical parking spaces.

Each slot belongs to a ParkingType and tracks its current occupancy.
Slots are auto-generated during seeding: VIP-001…VIP-010, STD-001…STD-350, etc.
"""

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from src.database.base import Base, TimestampMixin

# Allowed values for the `status` column
SLOT_STATUS_AVAILABLE = "available"
SLOT_STATUS_RESERVED = "reserved"
SLOT_STATUS_OCCUPIED = "occupied"
SLOT_STATUS_MAINTENANCE = "maintenance"

VALID_SLOT_STATUSES = {
    SLOT_STATUS_AVAILABLE,
    SLOT_STATUS_RESERVED,
    SLOT_STATUS_OCCUPIED,
    SLOT_STATUS_MAINTENANCE,
}


class ParkingSlot(Base, TimestampMixin):
    """Individual physical parking space."""

    __tablename__ = "parking_slots"
    __table_args__ = (
        UniqueConstraint("slot_number", name="uq_parking_slots_slot_number"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Human-readable identifier, e.g. "VIP-001", "STD-042"
    slot_number = Column(String(20), nullable=False)

    parking_type_id = Column(
        Integer,
        ForeignKey("parking_types.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Floor label, e.g. "Ground", "P1", "P2"
    floor_number = Column(String(10), nullable=True)

    # Current occupancy state
    status = Column(String(20), default=SLOT_STATUS_AVAILABLE, nullable=False)

    # FK to the booking currently using this slot (NULL when free)
    current_booking_id = Column(
        Integer,
        ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
    )

    # FK to the legacy reservation that pre-reserved this slot (NULL when free).
    # Set when status='reserved' (pending booking); cleared on approval/rejection.
    reservation_id = Column(Integer, nullable=True)

    # Relationships
    parking_type = relationship("ParkingType", back_populates="slots")
    current_booking = relationship(
        "Booking",
        foreign_keys=[current_booking_id],
        uselist=False,
    )

    def __repr__(self) -> str:
        return f"<ParkingSlot {self.slot_number!r} status={self.status!r}>"
