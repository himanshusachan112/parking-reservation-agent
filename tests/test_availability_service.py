"""
Tests for AvailabilityService.

Uses in-memory SQLite with production models.
"""

import pytest
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.base import Base
from src.models import ParkingType, ParkingSlot
from src.services.availability_service import AvailabilityService


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def db(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="module")
def seed_types(engine):
    """Seed parking types once for the module."""
    Session = sessionmaker(bind=engine)
    db = Session()
    types_data = [
        dict(
            slug="avail_std",
            name="Standard",
            total_slots=100,
            available_slots=60,
            hourly_price=Decimal("50"),
            daily_price=Decimal("350"),
            monthly_price=Decimal("4500"),
        ),
        dict(
            slug="avail_vip",
            name="VIP",
            total_slots=10,
            available_slots=0,
            hourly_price=Decimal("200"),
            daily_price=Decimal("1500"),
            monthly_price=Decimal("18000"),
        ),
        dict(
            slug="avail_ev",
            name="EV Charging",
            total_slots=40,
            available_slots=20,
            hourly_price=Decimal("120"),
            daily_price=Decimal("800"),
            monthly_price=Decimal("9500"),
        ),
    ]
    for td in types_data:
        if not db.query(ParkingType).filter_by(slug=td["slug"]).first():
            pt = ParkingType(is_active=True, features=[], **td)
            db.add(pt)
    db.commit()
    db.close()


class TestAvailabilityService:
    def setup_method(self):
        self.svc = AvailabilityService()

    def test_get_summary_returns_all_active(self, db, seed_types):
        summary = self.svc.get_summary(db)
        slugs = [s["slug"] for s in summary]
        assert "avail_std" in slugs
        assert "avail_vip" in slugs
        assert "avail_ev" in slugs

    def test_get_for_type_known_slug(self, db, seed_types):
        result = self.svc.get_for_type(db, "avail_std")
        assert result is not None
        assert result["slug"] == "avail_std"
        assert result["available_slots"] == 60
        assert result["total_slots"] == 100
        assert result["availability_percentage"] == 60

    def test_get_for_type_unknown_returns_none(self, db, seed_types):
        result = self.svc.get_for_type(db, "no_such_type_xyz")
        assert result is None

    def test_full_type_status(self, db, seed_types):
        result = self.svc.get_for_type(db, "avail_vip")
        assert result["is_available"] is False
        assert result["availability_status"] == "full"

    def test_available_type_status(self, db, seed_types):
        result = self.svc.get_for_type(db, "avail_std")
        assert result["is_available"] is True
        assert result["availability_status"] == "available"  # 60% ≥ 50%

    def test_limited_type_status(self, db, seed_types):
        result = self.svc.get_for_type(db, "avail_ev")
        assert result["is_available"] is True
        assert result["availability_status"] == "limited"  # 50% – just on boundary

    def test_get_alternatives_excludes_requested(self, db, seed_types):
        alts = self.svc.get_alternatives(db, "avail_vip")
        slugs = [a["slug"] for a in alts]
        assert "avail_vip" not in slugs
        # Should include other types with available_slots > 0
        assert "avail_std" in slugs

    def test_decrement_reduces_available(self, db, seed_types):
        pt = db.query(ParkingType).filter_by(slug="avail_std").first()
        before = pt.available_slots
        self.svc.decrement(db, pt.id)
        db.refresh(pt)
        assert pt.available_slots == before - 1

    def test_increment_restores_available(self, db, seed_types):
        pt = db.query(ParkingType).filter_by(slug="avail_std").first()
        before = pt.available_slots
        self.svc.increment(db, pt.id)
        db.refresh(pt)
        assert pt.available_slots == before + 1

    def test_decrement_floors_at_zero(self, db, seed_types):
        """VIP type already has 0 slots – decrement should have no effect."""
        pt = db.query(ParkingType).filter_by(slug="avail_vip").first()
        result = self.svc.decrement(db, pt.id)
        assert result is False  # rowcount = 0, no update
        db.refresh(pt)
        assert pt.available_slots == 0

    def test_summary_contains_pricing(self, db, seed_types):
        summary = self.svc.get_summary(db)
        std = next(s for s in summary if s["slug"] == "avail_std")
        assert std["hourly_price"] == 50.0
        assert std["daily_price"] == 350.0
        assert std["monthly_price"] == 4500.0
