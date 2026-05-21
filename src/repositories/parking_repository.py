"""
ParkingRepository – DB queries for ParkingType records.

All mutating methods require a caller-managed Session so they can
participate in larger transactions (e.g. approval + slot decrement).
"""

from typing import Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.models.parking_type import ParkingType


class ParkingRepository:
    """CRUD + slot management for the parking_types table."""

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_all_active(self, db: Session) -> List[ParkingType]:
        """Return all active parking types ordered by id."""
        return (
            db.execute(
                select(ParkingType)
                .where(ParkingType.is_active.is_(True))
                .order_by(ParkingType.id)
            )
            .scalars()
            .all()
        )

    def get_by_id(self, db: Session, parking_type_id: int) -> Optional[ParkingType]:
        return db.get(ParkingType, parking_type_id)

    def get_by_slug(self, db: Session, slug: str) -> Optional[ParkingType]:
        return db.execute(
            select(ParkingType).where(ParkingType.slug == slug.lower())
        ).scalar_one_or_none()

    def get_available_types(self, db: Session) -> List[ParkingType]:
        """Return only types that currently have at least one free slot."""
        return (
            db.execute(
                select(ParkingType)
                .where(ParkingType.is_active.is_(True))
                .where(ParkingType.available_slots > 0)
                .order_by(ParkingType.id)
            )
            .scalars()
            .all()
        )

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def create(self, db: Session, **kwargs) -> ParkingType:
        """Insert a new ParkingType.  Caller commits."""
        pt = ParkingType(**kwargs)
        db.add(pt)
        db.flush()  # populate pt.id without full commit
        return pt

    def upsert(self, db: Session, slug: str, **kwargs) -> ParkingType:
        """Insert or update a ParkingType by slug.  Caller commits."""
        existing = self.get_by_slug(db, slug)
        if existing:
            for k, v in kwargs.items():
                setattr(existing, k, v)
            db.flush()
            return existing
        return self.create(db, slug=slug, **kwargs)

    def decrement_available(self, db: Session, parking_type_id: int) -> bool:
        """
        Atomically decrement available_slots by 1 (floor 0).

        Returns True if a row was updated, False if already at 0.
        """
        result = db.execute(
            update(ParkingType)
            .where(ParkingType.id == parking_type_id)
            .where(ParkingType.available_slots > 0)
            .values(available_slots=ParkingType.available_slots - 1)
        )
        return result.rowcount > 0

    def increment_available(self, db: Session, parking_type_id: int) -> bool:
        """
        Atomically increment available_slots by 1 (ceiling = total_slots).

        Returns True if a row was updated.
        """
        result = db.execute(
            update(ParkingType)
            .where(ParkingType.id == parking_type_id)
            .where(ParkingType.available_slots < ParkingType.total_slots)
            .values(available_slots=ParkingType.available_slots + 1)
        )
        return result.rowcount > 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def to_dict(self, pt: ParkingType) -> Dict:
        return {
            "id": pt.id,
            "name": pt.name,
            "slug": pt.slug,
            "description": pt.description,
            "total_slots": pt.total_slots,
            "available_slots": pt.available_slots,
            "hourly_price": float(pt.hourly_price) if pt.hourly_price else None,
            "daily_price": float(pt.daily_price) if pt.daily_price else None,
            "monthly_price": float(pt.monthly_price) if pt.monthly_price else None,
            "features": pt.features or [],
            "is_active": pt.is_active,
            "availability_percentage": pt.availability_percentage,
            "is_available": pt.is_available,
            "availability_status": pt.availability_status,
        }
