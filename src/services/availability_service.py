"""
AvailabilityService – real-time slot availability queries and updates.

Wraps ParkingRepository to provide higher-level availability semantics,
including live status labels and alternative suggestions when a type is full.
"""

from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.repositories.parking_repository import ParkingRepository

_repo = ParkingRepository()


class AvailabilityService:
    """Query and update live parking slot availability."""

    def get_summary(self, db: Session) -> List[Dict]:
        """
        Return availability for ALL active parking types.

        Each entry includes:
          slug, name, available_slots, total_slots,
          availability_percentage, availability_status, is_available
        """
        types = _repo.get_all_active(db)
        return [self._type_summary(pt) for pt in types]

    def get_for_type(self, db: Session, slug: str) -> Optional[Dict]:
        """Return availability for a single parking type by slug."""
        pt = _repo.get_by_slug(db, slug)
        if pt is None:
            return None
        return self._type_summary(pt)

    def get_alternatives(self, db: Session, unavailable_slug: str) -> List[Dict]:
        """
        Return other available types when the requested one is full.
        Sorted by hourly price ascending.
        """
        avail = _repo.get_available_types(db)
        return [self._type_summary(pt) for pt in avail if pt.slug != unavailable_slug]

    # ------------------------------------------------------------------
    # Slot count mutations (called by BookingService on approve/cancel)
    # ------------------------------------------------------------------

    def decrement(self, db: Session, parking_type_id: int) -> bool:
        """Decrement available_slots by 1 (on approval).  Caller commits."""
        return _repo.decrement_available(db, parking_type_id)

    def increment(self, db: Session, parking_type_id: int) -> bool:
        """Increment available_slots by 1 (on cancel/reject).  Caller commits."""
        return _repo.increment_available(db, parking_type_id)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _type_summary(pt) -> Dict:
        return {
            "id": pt.slug,          # slug used as stable frontend identifier
            "slug": pt.slug,
            "name": pt.name,
            "description": pt.description,
            "available_slots": pt.available_slots,
            "total_slots": pt.total_slots,
            "availability_percentage": pt.availability_percentage,
            "availability_status": pt.availability_status,
            "is_available": pt.is_available,
            "hourly_price": float(pt.hourly_price) if pt.hourly_price else None,
            "daily_price": float(pt.daily_price) if pt.daily_price else None,
            "monthly_price": float(pt.monthly_price) if pt.monthly_price else None,
            "features": pt.features or [],
        }
