"""
BookingService – orchestrates the full booking lifecycle.

Key operations
--------------
* `create`         – validate + insert a Booking (status=pending)
* `approve`        – validate slot availability, allocate slot, decrement
                     parking_type.available_slots, log AdminAction
* `reject`         – update status, no slot change, log AdminAction
* `cancel`         – release slot if assigned, increment available_slots
* `get` / `list`   – thin wrappers over BookingRepository

All mutating methods open their own Session (via `db_session()`) so callers
don't need to manage transactions.  The session is committed only after all
steps succeed – rolled back automatically on any exception.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.database.session import db_session
from src.models.admin_action import AdminAction
from src.models.booking import (
    BOOKING_APPROVED,
    BOOKING_CANCELLED,
    BOOKING_REJECTED,
    Booking,
)
from src.repositories.booking_repository import BookingRepository
from src.repositories.parking_repository import ParkingRepository
from src.repositories.slot_repository import SlotRepository
from src.services.availability_service import AvailabilityService
from src.services.booking_validation_service import (
    BookingValidationError,
    BookingValidationService,
)
from src.services.pricing_service import PricingService

logger = logging.getLogger(__name__)

_booking_repo = BookingRepository()
_parking_repo = ParkingRepository()
_slot_repo = SlotRepository()
_avail_svc = AvailabilityService()
_pricing_svc = PricingService()
_validation_svc = BookingValidationService()


class BookingServiceError(RuntimeError):
    """Raised by BookingService for recoverable business-logic failures."""


class BookingService:
    """High-level booking lifecycle operations."""

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def create(
        self,
        parking_type_slug: str,
        user_name: str,
        email: Optional[str],
        vehicle_number: str,
        start_time: datetime,
        end_time: datetime,
        vehicle_type: Optional[str] = None,
        legacy_reservation_id: Optional[int] = None,
    ) -> Dict:
        """
        Create a new booking in *pending* status.

        Validates availability and business rules before inserting.
        Calculates and stores the INR price.

        Returns the serialised Booking dict.
        Raises BookingValidationError on rule violations.
        """
        with db_session() as db:
            pt = _parking_repo.get_by_slug(db, parking_type_slug)
            if pt is None:
                raise BookingServiceError(
                    f"Parking type '{parking_type_slug}' not found."
                )

            _validation_svc.validate_or_raise(
                db,
                parking_type_slug,
                start_time,
                end_time,
                vehicle_number,
                email,
            )

            price_info = _pricing_svc.calculate_from_type(pt, start_time, end_time)

            booking = _booking_repo.create(
                db,
                parking_type_id=pt.id,
                user_name=user_name,
                email=email.lower() if email else None,
                vehicle_number=vehicle_number.upper(),
                vehicle_type=vehicle_type,
                start_time=start_time,
                end_time=end_time,
                total_price=price_info.total_inr,
                booking_duration_hours=price_info.duration_hours,
                legacy_reservation_id=legacy_reservation_id,
            )
            db.commit()
            db.refresh(booking)
            result = _booking_repo.to_dict(booking)

        logger.info(
            "Booking created ref=%s user=%s type=%s",
            result["booking_reference"],
            user_name,
            parking_type_slug,
        )
        return result

    # ------------------------------------------------------------------
    # APPROVE
    # ------------------------------------------------------------------

    def approve(
        self,
        booking_id: int,
        admin_email: Optional[str] = None,
        admin_notes: Optional[str] = None,
    ) -> Dict:
        """
        Approve a pending booking.

        Steps (all in one transaction):
          1. Load booking – must be pending
          2. Validate slot still available
          3. Allocate first available physical slot
          4. Decrement parking_type.available_slots
          5. Update booking.status = approved + approved_at
          6. Log AdminAction
        """
        with db_session() as db:
            booking = _booking_repo.get_by_id(db, booking_id)
            if booking is None:
                raise BookingServiceError(f"Booking #{booking_id} not found.")
            if booking.status != "pending":
                raise BookingServiceError(
                    f"Booking #{booking_id} is already '{booking.status}'."
                )

            pt = booking.parking_type
            if not pt.is_available:
                alternatives = _avail_svc.get_alternatives(db, pt.slug)
                raise BookingValidationError(
                    f"No slots available for '{pt.name}'.",
                    alternatives=alternatives,
                )

            # Allocate physical slot
            slot = _slot_repo.allocate_first_available(db, pt.id, booking.id)
            if slot:
                booking.assigned_slot_id = slot.id

            # Decrement inventory counter
            _avail_svc.decrement(db, pt.id)

            # Update booking record
            _booking_repo.update_status(db, booking, BOOKING_APPROVED, admin_notes)

            # Audit log
            action = AdminAction(
                booking_id=booking.id,
                action=BOOKING_APPROVED,
                admin_email=admin_email,
                remarks=admin_notes,
            )
            db.add(action)
            db.commit()
            db.refresh(booking)
            result = _booking_repo.to_dict(booking)

        logger.info(
            "Booking #%d approved ref=%s slot=%s",
            booking_id,
            result["booking_reference"],
            result.get("assigned_slot"),
        )
        return result

    # ------------------------------------------------------------------
    # REJECT
    # ------------------------------------------------------------------

    def reject(
        self,
        booking_id: int,
        admin_email: Optional[str] = None,
        admin_notes: Optional[str] = None,
    ) -> Dict:
        """
        Reject a pending booking.

        Releases any pre-reserved physical slot back to AVAILABLE and
        increments parking_type.available_slots so the counter is restored.
        Logs an AdminAction.
        """
        with db_session() as db:
            booking = _booking_repo.get_by_id(db, booking_id)
            if booking is None:
                raise BookingServiceError(f"Booking #{booking_id} not found.")
            if booking.status != "pending":
                raise BookingServiceError(
                    f"Booking #{booking_id} is already '{booking.status}'."
                )

            slot_number = None

            # Release the pre-reserved slot back to AVAILABLE
            if booking.assigned_slot_id:
                slot = _slot_repo.get_by_id(db, booking.assigned_slot_id)
                if slot:
                    slot_number = slot.slot_number
                    logger.info(
                        "Releasing slot %s from booking #%d",
                        slot.slot_number, booking_id,
                    )
                    _slot_repo.release(db, slot)
                    old_count = booking.parking_type.available_slots
                    _avail_svc.increment(db, booking.parking_type_id)
                    logger.info(
                        "%s available_slots updated: %d \u2192 %d",
                        booking.parking_type.name,
                        old_count,
                        old_count + 1,
                    )

            _booking_repo.update_status(db, booking, BOOKING_REJECTED, admin_notes)

            action = AdminAction(
                booking_id=booking.id,
                action=BOOKING_REJECTED,
                admin_email=admin_email,
                remarks=admin_notes,
            )
            db.add(action)
            db.commit()
            db.refresh(booking)
            result = _booking_repo.to_dict(booking)

        logger.info(
            "Booking #%d rejected ref=%s slot_released=%s",
            booking_id, result["booking_reference"], slot_number,
        )
        return result

    # ------------------------------------------------------------------
    # CANCEL
    # ------------------------------------------------------------------

    def cancel(self, booking_id: int, reason: Optional[str] = None) -> Dict:
        """
        Cancel an approved (or pending) booking.

        Releases the assigned slot and increments available_slots.
        """
        with db_session() as db:
            booking = _booking_repo.get_by_id(db, booking_id)
            if booking is None:
                raise BookingServiceError(f"Booking #{booking_id} not found.")
            if booking.status in {BOOKING_CANCELLED, "completed", BOOKING_REJECTED}:
                raise BookingServiceError(
                    f"Cannot cancel a booking with status '{booking.status}'."
                )

            # Release slot if one was assigned
            if booking.assigned_slot_id:
                slot = _slot_repo.get_by_id(db, booking.assigned_slot_id)
                if slot:
                    _slot_repo.release(db, slot)
                _avail_svc.increment(db, booking.parking_type_id)

            _booking_repo.update_status(db, booking, BOOKING_CANCELLED, reason)
            db.commit()
            db.refresh(booking)
            result = _booking_repo.to_dict(booking)

        logger.info("Booking #%d cancelled", booking_id)
        return result

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def get(self, booking_id: int) -> Optional[Dict]:
        with db_session() as db:
            booking = _booking_repo.get_by_id(db, booking_id)
            return _booking_repo.to_dict(booking) if booking else None

    def get_by_reference(self, reference: str) -> Optional[Dict]:
        with db_session() as db:
            booking = _booking_repo.get_by_reference(db, reference)
            return _booking_repo.to_dict(booking) if booking else None

    def list(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict]:
        with db_session() as db:
            bookings = _booking_repo.get_all(
                db, limit=limit, offset=offset, status=status
            )
            return [_booking_repo.to_dict(b) for b in bookings]

    def list_by_email(self, email: str) -> List[Dict]:
        with db_session() as db:
            bookings = _booking_repo.get_by_email(db, email.lower())
            return [_booking_repo.to_dict(b) for b in bookings]
