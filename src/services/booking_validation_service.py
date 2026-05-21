"""
BookingValidationService – pre-submission and pre-approval validation rules.

Rules enforced
--------------
1. Parking type exists and is active.
2. At least one slot is available for the requested type.
3. `start_time` is at least 1 hour in the future.
4. `end_time` > `start_time`.
5. Booking duration is between 1 hour and 30 days.
6. No overlapping approved/pending booking for the SAME user + vehicle.

On validation failure the service raises `BookingValidationError` with a
human-readable message and (optionally) a list of alternative parking types.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from src.repositories.booking_repository import BookingRepository
from src.repositories.parking_repository import ParkingRepository
from src.services.availability_service import AvailabilityService

_parking_repo = ParkingRepository()
_booking_repo = BookingRepository()
_avail_svc = AvailabilityService()

MIN_ADVANCE_HOURS = 1
MAX_DURATION_DAYS = 30


class BookingValidationError(ValueError):
    """Raised when a booking request violates a business rule."""

    def __init__(self, message: str, alternatives: Optional[List[dict]] = None):
        super().__init__(message)
        self.alternatives = alternatives or []


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    alternatives: List[dict] = field(default_factory=list)

    @property
    def first_error(self) -> Optional[str]:
        return self.errors[0] if self.errors else None


class BookingValidationService:
    """Validate a booking request against business rules."""

    def validate(
        self,
        db: Session,
        parking_type_slug: str,
        start_time: datetime,
        end_time: datetime,
        vehicle_number: str,
        email: Optional[str] = None,
        exclude_booking_id: Optional[int] = None,
    ) -> ValidationResult:
        """
        Run all validation rules.

        Returns a `ValidationResult`. Callers may also call `validate_or_raise`
        to get an exception on the first failure.
        """
        errors: List[str] = []
        alternatives: List[dict] = []

        # 1. Parking type must exist
        pt = _parking_repo.get_by_slug(db, parking_type_slug)
        if pt is None or not pt.is_active:
            errors.append(f"Parking type '{parking_type_slug}' is not available.")
            return ValidationResult(is_valid=False, errors=errors)

        # 2. Availability
        if not pt.is_available:
            alternatives = _avail_svc.get_alternatives(db, parking_type_slug)
            errors.append(
                f"No slots available for '{pt.name}'. "
                f"{len(alternatives)} alternative type(s) available."
            )

        # 3. start must be in the future (at least MIN_ADVANCE_HOURS from now)
        now = datetime.now(timezone.utc)
        start_aware = (
            start_time if start_time.tzinfo else start_time.replace(tzinfo=timezone.utc)
        )
        end_aware = (
            end_time if end_time.tzinfo else end_time.replace(tzinfo=timezone.utc)
        )

        min_start = now + timedelta(hours=MIN_ADVANCE_HOURS)
        if start_aware < min_start:
            errors.append(
                f"Booking must be at least {MIN_ADVANCE_HOURS} hour(s) in the future."
            )

        # 4. end > start
        if end_aware <= start_aware:
            errors.append("End time must be after start time.")

        # 5. Duration limits
        if end_aware > start_aware:
            duration_hours = (end_aware - start_aware).total_seconds() / 3600
            if duration_hours < 1:
                errors.append("Minimum booking duration is 1 hour.")
            if duration_hours > MAX_DURATION_DAYS * 24:
                errors.append(f"Maximum booking duration is {MAX_DURATION_DAYS} days.")

        # 6. Overlap check for this vehicle
        if vehicle_number and pt.id:
            overlap = _booking_repo.has_overlapping_booking(
                db,
                parking_type_id=pt.id,
                start_time=start_aware,
                end_time=end_aware,
                vehicle_number=vehicle_number,
                exclude_booking_id=exclude_booking_id,
            )
            if overlap:
                errors.append(
                    f"Vehicle '{vehicle_number}' already has an active booking "
                    "for this parking type during the requested period."
                )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            alternatives=alternatives,
        )

    def validate_or_raise(
        self,
        db: Session,
        parking_type_slug: str,
        start_time: datetime,
        end_time: datetime,
        vehicle_number: str,
        email: Optional[str] = None,
        exclude_booking_id: Optional[int] = None,
    ) -> None:
        """Raise `BookingValidationError` on the first validation failure."""
        result = self.validate(
            db,
            parking_type_slug,
            start_time,
            end_time,
            vehicle_number,
            email,
            exclude_booking_id,
        )
        if not result.is_valid:
            raise BookingValidationError(
                result.first_error or "Booking validation failed.",
                alternatives=result.alternatives,
            )
