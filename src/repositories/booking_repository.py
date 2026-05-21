"""
BookingRepository – DB queries for the Booking lifecycle table.
"""

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, joinedload

from src.models.booking import (
    BOOKING_APPROVED,
    BOOKING_CANCELLED,
    BOOKING_COMPLETED,
    BOOKING_PENDING,
    BOOKING_REJECTED,
    Booking,
)


class BookingRepository:
    """CRUD operations for the bookings table."""

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_by_id(self, db: Session, booking_id: int) -> Optional[Booking]:
        return db.execute(
            select(Booking)
            .options(
                joinedload(Booking.parking_type),
                joinedload(Booking.assigned_slot),
            )
            .where(Booking.id == booking_id)
        ).scalar_one_or_none()

    def get_by_reference(self, db: Session, reference: str) -> Optional[Booking]:
        return db.execute(
            select(Booking).where(Booking.booking_reference == reference.upper())
        ).scalar_one_or_none()

    def get_by_status(self, db: Session, status: str) -> List[Booking]:
        return (
            db.execute(
                select(Booking)
                .options(joinedload(Booking.parking_type))
                .where(Booking.status == status)
                .order_by(Booking.created_at.desc())
            )
            .scalars()
            .all()
        )

    def get_pending(self, db: Session) -> List[Booking]:
        return self.get_by_status(db, BOOKING_PENDING)

    def get_by_email(self, db: Session, email: str) -> List[Booking]:
        return (
            db.execute(
                select(Booking)
                .options(joinedload(Booking.parking_type))
                .where(Booking.email == email.lower())
                .order_by(Booking.created_at.desc())
            )
            .scalars()
            .all()
        )

    def get_all(
        self,
        db: Session,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> List[Booking]:
        q = select(Booking).options(joinedload(Booking.parking_type))
        if status:
            q = q.where(Booking.status == status)
        q = q.order_by(Booking.created_at.desc()).limit(limit).offset(offset)
        return db.execute(q).scalars().all()

    def has_overlapping_booking(
        self,
        db: Session,
        parking_type_id: int,
        start_time: datetime,
        end_time: datetime,
        vehicle_number: str,
        exclude_booking_id: Optional[int] = None,
    ) -> bool:
        """
        Return True if the SAME VEHICLE already has an active booking for
        the same parking type overlapping with [start_time, end_time].

        We scope to vehicle_number so different customers can book the same
        parking TYPE concurrently (slots are managed via available_slots counter).
        """
        q = (
            select(Booking.id)
            .where(Booking.parking_type_id == parking_type_id)
            .where(Booking.vehicle_number == vehicle_number.upper())
            .where(Booking.status.in_([BOOKING_PENDING, BOOKING_APPROVED]))
            .where(
                and_(
                    Booking.start_time < end_time,
                    Booking.end_time > start_time,
                )
            )
        )
        if exclude_booking_id:
            q = q.where(Booking.id != exclude_booking_id)
        result = db.execute(q).first()
        return result is not None

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def create(self, db: Session, **kwargs) -> Booking:
        booking = Booking(**kwargs)
        db.add(booking)
        db.flush()
        return booking

    def update_status(
        self,
        db: Session,
        booking: Booking,
        status: str,
        admin_notes: Optional[str] = None,
    ) -> Booking:
        booking.status = status
        if admin_notes is not None:
            booking.admin_notes = admin_notes
        if status == BOOKING_APPROVED:
            from datetime import timezone

            booking.approved_at = datetime.now(timezone.utc)
        db.flush()
        return booking

    def assign_slot(
        self,
        db: Session,
        booking: Booking,
        slot_id: int,
    ) -> Booking:
        booking.assigned_slot_id = slot_id
        db.flush()
        return booking

    def set_price(
        self,
        db: Session,
        booking: Booking,
        total_price: float,
        duration_hours: float,
    ) -> Booking:
        booking.total_price = total_price
        booking.booking_duration_hours = duration_hours
        db.flush()
        return booking

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def to_dict(self, b: Booking) -> Dict:
        return {
            "id": b.id,
            "booking_reference": b.booking_reference,
            "user_name": b.user_name,
            "email": b.email,
            "vehicle_number": b.vehicle_number,
            "vehicle_type": b.vehicle_type,
            "parking_type_id": b.parking_type_id,
            "parking_type": b.parking_type.slug if b.parking_type else None,
            "parking_type_name": b.parking_type.name if b.parking_type else None,
            "assigned_slot": b.assigned_slot.slot_number if b.assigned_slot else None,
            "start_time": b.start_time.isoformat() if b.start_time else None,
            "end_time": b.end_time.isoformat() if b.end_time else None,
            "total_price": float(b.total_price) if b.total_price else None,
            "booking_duration_hours": b.booking_duration_hours,
            "status": b.status,
            "admin_notes": b.admin_notes,
            "created_at": b.created_at.isoformat() if b.created_at else None,
            "updated_at": b.updated_at.isoformat() if b.updated_at else None,
            "approved_at": b.approved_at.isoformat() if b.approved_at else None,
        }
