"""
AdminAction model – immutable audit log of every admin decision.

Each approve/reject creates a new row here. This provides a full audit trail
without mutating the Booking record itself.
"""

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from src.database.base import Base, TimestampMixin


class AdminAction(Base, TimestampMixin):
    """Immutable audit record of an admin approve/reject action."""

    __tablename__ = "admin_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    booking_id = Column(
        Integer,
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
    )

    # "approved" | "rejected" | "cancelled"
    action = Column(String(20), nullable=False)

    # Who performed the action (email or system)
    admin_email = Column(String(200), nullable=True)

    # Optional free-text reason / note
    remarks = Column(Text, nullable=True)

    # Relationship
    booking = relationship("Booking", back_populates="admin_actions")

    def __repr__(self) -> str:
        return f"<AdminAction booking_id={self.booking_id} " f"action={self.action!r}>"
