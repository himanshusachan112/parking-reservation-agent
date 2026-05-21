"""
ParkingType model – master catalogue of parking space categories.

Each row represents one category (standard, large, ev, vip, disabled, bike).
The `available_slots` column is decremented/incremented atomically by the
SlotAllocationService to give real-time availability without a full JOIN.
"""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from src.database.base import Base, TimestampMixin


class ParkingType(Base, TimestampMixin):
    """Master catalogue of parking space categories."""

    __tablename__ = "parking_types"
    __table_args__ = (UniqueConstraint("slug", name="uq_parking_types_slug"),)

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Human-readable name and machine-friendly slug
    name = Column(String(100), nullable=False)
    slug = Column(String(50), nullable=False)  # "standard", "vip", etc.
    description = Column(String(500), nullable=True)

    # Slot inventory – updated atomically on each approval / cancellation
    total_slots = Column(Integer, default=0, nullable=False)
    available_slots = Column(Integer, default=0, nullable=False)

    # Pricing in INR – never USD
    hourly_price = Column(Numeric(10, 2), nullable=False)
    daily_price = Column(Numeric(10, 2), nullable=True)
    monthly_price = Column(Numeric(10, 2), nullable=True)

    # Array of feature strings, e.g. ["CCTV", "Covered"]
    features = Column(JSON, nullable=True, default=list)

    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    slots = relationship("ParkingSlot", back_populates="parking_type", lazy="dynamic")
    bookings = relationship("Booking", back_populates="parking_type", lazy="dynamic")

    def __repr__(self) -> str:
        return (
            f"<ParkingType id={self.id} slug={self.slug!r} "
            f"available={self.available_slots}/{self.total_slots}>"
        )

    @property
    def availability_percentage(self) -> int:
        if not self.total_slots:
            return 0
        return round((self.available_slots / self.total_slots) * 100)

    @property
    def is_available(self) -> bool:
        return self.available_slots > 0

    @property
    def availability_status(self) -> str:
        pct = self.availability_percentage
        if pct > 50:
            return "available"
        if pct > 0:
            return "limited"
        return "full"
