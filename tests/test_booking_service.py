"""
Tests for BookingService.

Uses in-memory SQLite with full production model schema.
Patches `db_session` to inject the test session so BookingService
doesn't open its own real-DB connections.
"""

import pytest
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.base import Base
from src.models import ParkingType, ParkingSlot, Booking, AdminAction
from src.services.booking_service import BookingService, BookingServiceError
from src.services.booking_validation_service import BookingValidationError

# ── In-memory SQLite setup ───────────────────────────────────────────────────
_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(_engine)
_Session = sessionmaker(bind=_engine, expire_on_commit=False)


@contextmanager
def _test_db_session():
    """Replacement for src.database.session.db_session used in services."""
    db = _Session()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def patch_db_session():
    """Patch db_session() calls in booking_service and parking_service."""
    targets = [
        "src.services.booking_service.db_session",
        "src.services.parking_service.db_session",
    ]
    patches = [patch(t, _test_db_session) for t in targets]
    for p in patches:
        p.start()
    yield
    for p in patches:
        p.stop()


@pytest.fixture
def parking_type():
    """Create a standard parking type with 5 available slots."""
    db = _Session()
    pt = db.query(ParkingType).filter_by(slug="bsvc_std").first()
    if not pt:
        pt = ParkingType(
            slug="bsvc_std",
            name="Standard",
            total_slots=10,
            available_slots=5,
            hourly_price=Decimal("50"),
            daily_price=Decimal("350"),
            monthly_price=Decimal("4500"),
            is_active=True,
            features=[],
        )
        db.add(pt)
        db.commit()
    db.close()
    return pt


@pytest.fixture
def full_parking_type():
    """Create a parking type with 0 available slots."""
    db = _Session()
    pt = db.query(ParkingType).filter_by(slug="bsvc_full").first()
    if not pt:
        pt = ParkingType(
            slug="bsvc_full",
            name="Full Type",
            total_slots=5,
            available_slots=0,
            hourly_price=Decimal("80"),
            is_active=True,
            features=[],
        )
        db.add(pt)
        db.commit()
    db.close()
    return pt


def _future(hours=2.0) -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=hours)


# ── Test class ────────────────────────────────────────────────────────────────


class TestBookingService:
    def setup_method(self):
        self.svc = BookingService()

    # ------------------------------------------------------------------
    # create
    # ------------------------------------------------------------------

    def test_create_returns_booking_dict(self, parking_type):
        start = _future(2)
        end = start + timedelta(hours=4)
        result = self.svc.create(
            parking_type_slug=parking_type.slug,
            user_name="Test User",
            email="test@example.com",
            vehicle_number="TS01AB1234",
            start_time=start,
            end_time=end,
        )
        assert result["status"] == "pending"
        assert result["booking_reference"].startswith("PS-")
        assert result["parking_type"] == parking_type.slug
        assert result["total_price"] == 200.0  # 4 × ₹50

    def test_create_generates_unique_references(self, parking_type):
        start = _future(3)
        end = start + timedelta(hours=2)
        r1 = self.svc.create(
            parking_type_slug=parking_type.slug,
            user_name="A",
            email=None,
            vehicle_number="TS99AA0001",
            start_time=start,
            end_time=end,
        )
        r2 = self.svc.create(
            parking_type_slug=parking_type.slug,
            user_name="B",
            email=None,
            vehicle_number="TS99AA0002",
            start_time=start,
            end_time=end,
        )
        assert r1["booking_reference"] != r2["booking_reference"]

    def test_create_full_type_raises_validation_error(self, full_parking_type):
        start = _future(2)
        end = start + timedelta(hours=2)
        with pytest.raises(BookingValidationError):
            self.svc.create(
                parking_type_slug=full_parking_type.slug,
                user_name="X",
                email=None,
                vehicle_number="TS00ZZ9999",
                start_time=start,
                end_time=end,
            )

    def test_create_unknown_type_raises(self):
        start = _future(2)
        end = start + timedelta(hours=2)
        with pytest.raises((BookingServiceError, BookingValidationError)):
            self.svc.create(
                parking_type_slug="nonexistent_zzz",
                user_name="X",
                email=None,
                vehicle_number="TS00ZZ0001",
                start_time=start,
                end_time=end,
            )

    # ------------------------------------------------------------------
    # approve / reject / cancel
    # ------------------------------------------------------------------

    def test_approve_changes_status(self, parking_type):
        start = _future(4)
        end = start + timedelta(hours=2)
        created = self.svc.create(
            parking_type_slug=parking_type.slug,
            user_name="Approve Me",
            email=None,
            vehicle_number="TS01APPROVE",
            start_time=start,
            end_time=end,
        )
        approved = self.svc.approve(created["id"])
        assert approved["status"] == "approved"
        assert approved["approved_at"] is not None

    def test_approve_nonexistent_raises(self):
        with pytest.raises(BookingServiceError):
            self.svc.approve(99999)

    def test_reject_changes_status(self, parking_type):
        start = _future(5)
        end = start + timedelta(hours=2)
        created = self.svc.create(
            parking_type_slug=parking_type.slug,
            user_name="Reject Me",
            email=None,
            vehicle_number="TS01REJECT",
            start_time=start,
            end_time=end,
        )
        rejected = self.svc.reject(created["id"], admin_notes="Sorry, full")
        assert rejected["status"] == "rejected"
        assert rejected["admin_notes"] == "Sorry, full"

    def test_cancel_pending_booking(self, parking_type):
        start = _future(6)
        end = start + timedelta(hours=2)
        created = self.svc.create(
            parking_type_slug=parking_type.slug,
            user_name="Cancel Me",
            email=None,
            vehicle_number="TS01CANCEL",
            start_time=start,
            end_time=end,
        )
        cancelled = self.svc.cancel(created["id"], reason="Changed plans")
        assert cancelled["status"] == "cancelled"

    # ------------------------------------------------------------------
    # read methods
    # ------------------------------------------------------------------

    def test_get_returns_dict(self, parking_type):
        start = _future(7)
        end = start + timedelta(hours=1)
        created = self.svc.create(
            parking_type_slug=parking_type.slug,
            user_name="Get Test",
            email=None,
            vehicle_number="TS01GET",
            start_time=start,
            end_time=end,
        )
        result = self.svc.get(created["id"])
        assert result is not None
        assert result["id"] == created["id"]

    def test_get_nonexistent_returns_none(self):
        assert self.svc.get(99999) is None

    def test_list_returns_list(self, parking_type):
        bookings = self.svc.list(limit=10)
        assert isinstance(bookings, list)

    def test_list_filter_by_status(self, parking_type):
        pending = self.svc.list(status="pending", limit=100)
        assert all(b["status"] == "pending" for b in pending)
