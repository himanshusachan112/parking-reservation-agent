"""
Tests for BookingValidationService.

All tests use an in-memory SQLite DB populated with test parking type data
via the production SQLAlchemy models.
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.base import Base
from src.models import ParkingType, ParkingSlot, Booking, AdminAction
from src.services.booking_validation_service import (
    BookingValidationService,
    BookingValidationError,
)


# ── Shared in-memory SQLite engine for this test module ─────────────────────
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


@pytest.fixture
def standard_type(db):
    """Insert a standard parking type with 10 available slots."""
    pt = db.query(ParkingType).filter_by(slug="standard_test").first()
    if not pt:
        pt = ParkingType(
            slug="standard_test",
            name="Standard Test",
            total_slots=10,
            available_slots=5,
            hourly_price=Decimal("50.00"),
            daily_price=Decimal("350.00"),
            monthly_price=Decimal("4500.00"),
            is_active=True,
        )
        db.add(pt)
        db.commit()
    return pt


@pytest.fixture
def full_type(db):
    """Insert a parking type with 0 available slots."""
    pt = db.query(ParkingType).filter_by(slug="full_test").first()
    if not pt:
        pt = ParkingType(
            slug="full_test",
            name="Full Type",
            total_slots=5,
            available_slots=0,
            hourly_price=Decimal("80.00"),
            is_active=True,
        )
        db.add(pt)
        db.commit()
    return pt


class TestBookingValidation:
    def setup_method(self):
        self.svc = BookingValidationService()

    def _future(self, hours_from_now: float = 2.0) -> datetime:
        return datetime.now(timezone.utc) + timedelta(hours=hours_from_now)

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_valid_booking(self, db, standard_type):
        start = self._future(2)
        end = start + timedelta(hours=4)
        result = self.svc.validate(db, standard_type.slug, start, end, "TS09AB1234")
        assert result.is_valid
        assert result.errors == []

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------

    def test_full_type_returns_alternatives(self, db, full_type, standard_type):
        start = self._future(2)
        end = start + timedelta(hours=2)
        result = self.svc.validate(db, full_type.slug, start, end, "TS09AB0001")
        assert not result.is_valid
        assert any("No slots" in e for e in result.errors)
        # Alternatives should include standard_test (available_slots > 0)
        alt_slugs = [a["slug"] for a in result.alternatives]
        assert standard_type.slug in alt_slugs

    # ------------------------------------------------------------------
    # Time constraints
    # ------------------------------------------------------------------

    def test_start_in_past_fails(self, db, standard_type):
        start = self._future(-2)  # 2 hours ago
        end = start + timedelta(hours=4)
        result = self.svc.validate(db, standard_type.slug, start, end, "TS01")
        assert not result.is_valid
        assert any("future" in e.lower() for e in result.errors)

    def test_end_before_start_fails(self, db, standard_type):
        start = self._future(2)
        end = start - timedelta(hours=1)
        result = self.svc.validate(db, standard_type.slug, start, end, "TS01")
        assert not result.is_valid
        assert any("after start" in e.lower() for e in result.errors)

    def test_max_duration_exceeded_fails(self, db, standard_type):
        start = self._future(2)
        end = start + timedelta(days=31)  # exceeds 30-day limit
        result = self.svc.validate(db, standard_type.slug, start, end, "TS01")
        assert not result.is_valid
        assert any("30 days" in e for e in result.errors)

    # ------------------------------------------------------------------
    # Unknown type
    # ------------------------------------------------------------------

    def test_unknown_type_fails(self, db):
        start = self._future(2)
        end = start + timedelta(hours=2)
        result = self.svc.validate(db, "nonexistent_xyz", start, end, "TS01")
        assert not result.is_valid

    # ------------------------------------------------------------------
    # validate_or_raise
    # ------------------------------------------------------------------

    def test_validate_or_raise_raises_on_failure(self, db, full_type):
        start = self._future(2)
        end = start + timedelta(hours=2)
        with pytest.raises(BookingValidationError) as exc_info:
            self.svc.validate_or_raise(db, full_type.slug, start, end, "TS09AB0001")
        assert exc_info.value.alternatives is not None

    def test_validate_or_raise_no_exception_on_success(self, db, standard_type):
        start = self._future(2)
        end = start + timedelta(hours=2)
        # Should not raise
        self.svc.validate_or_raise(db, standard_type.slug, start, end, "TS09AB9999")
