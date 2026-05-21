"""
SlotRepository – DB queries for individual ParkingSlot records.
"""

from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.models.parking_slot import (
    SLOT_STATUS_AVAILABLE,
    SLOT_STATUS_RESERVED,
    ParkingSlot,
)


class SlotRepository:
    """CRUD + allocation queries for the parking_slots table."""

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_by_id(self, db: Session, slot_id: int) -> Optional[ParkingSlot]:
        return db.get(ParkingSlot, slot_id)

    def get_by_number(self, db: Session, slot_number: str) -> Optional[ParkingSlot]:
        return db.execute(
            select(ParkingSlot).where(ParkingSlot.slot_number == slot_number.upper())
        ).scalar_one_or_none()

    def get_available_for_type(
        self, db: Session, parking_type_id: int, limit: int = 1
    ) -> List[ParkingSlot]:
        """Return up to `limit` available slots for a parking type (lowest id first)."""
        return (
            db.execute(
                select(ParkingSlot)
                .where(ParkingSlot.parking_type_id == parking_type_id)
                .where(ParkingSlot.status == SLOT_STATUS_AVAILABLE)
                .order_by(ParkingSlot.id)
                .limit(limit)
            )
            .scalars()
            .all()
        )

    def get_all_for_type(self, db: Session, parking_type_id: int) -> List[ParkingSlot]:
        return (
            db.execute(
                select(ParkingSlot)
                .where(ParkingSlot.parking_type_id == parking_type_id)
                .order_by(ParkingSlot.slot_number)
            )
            .scalars()
            .all()
        )

    def count_available(self, db: Session, parking_type_id: int) -> int:
        from sqlalchemy import func

        result = db.execute(
            select(func.count(ParkingSlot.id))
            .where(ParkingSlot.parking_type_id == parking_type_id)
            .where(ParkingSlot.status == SLOT_STATUS_AVAILABLE)
        ).scalar()
        return result or 0

    # ------------------------------------------------------------------
    # Writes (caller is responsible for commit)
    # ------------------------------------------------------------------

    def create(self, db: Session, **kwargs) -> ParkingSlot:
        slot = ParkingSlot(**kwargs)
        db.add(slot)
        db.flush()
        return slot

    def reserve(self, db: Session, slot: ParkingSlot, booking_id: int) -> ParkingSlot:
        """Mark a slot as reserved and link it to a booking."""
        slot.status = SLOT_STATUS_RESERVED
        slot.current_booking_id = booking_id
        db.flush()
        return slot

    def release(self, db: Session, slot: ParkingSlot) -> ParkingSlot:
        """Free a slot (cancellation / rejection)."""
        slot.status = SLOT_STATUS_AVAILABLE
        slot.current_booking_id = None
        db.flush()
        return slot

    def allocate_first_available(
        self, db: Session, parking_type_id: int, booking_id: int
    ) -> Optional[ParkingSlot]:
        """
        Find the first available slot for a type and reserve it atomically.

        Returns the reserved ParkingSlot, or None if no slots are free.
        """
        slots = self.get_available_for_type(db, parking_type_id, limit=1)
        if not slots:
            return None
        return self.reserve(db, slots[0], booking_id)
