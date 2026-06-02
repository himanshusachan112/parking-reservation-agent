"""
SQL Store Module - SQLite Database for Dynamic Parking Data.

This module handles:
- Working hours (change seasonally)
- Pricing information (can change anytime)
- Space availability (changes in real-time as cars park/leave)

WHY SQL FOR DYNAMIC DATA?
- Vector databases are great for semantic search on text
- But for structured, frequently-changing data (prices, counts), SQL is better:
  * Easy to UPDATE a single value (e.g., price change)
  * Exact queries (e.g., "how many spaces available?")
  * Transactional safety (no double-booking)
  * Much faster for simple lookups than vector search

We use SQLite because:
- Zero configuration (no server needed)
- Single file database (easy to deploy)
- Perfect for this scale of data
"""

import math
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from config.settings import settings

# SQLAlchemy base class for our models
Base = declarative_base()


# ========================
# DATABASE MODELS (Tables)
# ========================


class WorkingHours(Base):
    """
    Stores the opening and closing hours for each day of the week.
    Example: Monday -> 06:00 to 23:00
    """

    __tablename__ = "working_hours"

    id = Column(Integer, primary_key=True)
    day_of_week = Column(String, nullable=False, unique=True)  # Monday, Tuesday, etc.
    open_time = Column(String, nullable=False)  # "06:00"
    close_time = Column(String, nullable=False)  # "23:00"
    is_open = Column(Boolean, default=True)  # False if closed that day


class ParkingPrice(Base):
    """
    Stores pricing for different parking space types and durations.
    All prices are in INR (Indian Rupees ₹).
    """

    __tablename__ = "parking_prices"

    id = Column(Integer, primary_key=True)
    space_type = Column(String, nullable=False)  # "standard", "large", "ev", "vip"
    duration_type = Column(String, nullable=False)  # "hourly", "daily", "weekly", "monthly"
    price = Column(Float, nullable=False)  # Price in INR (₹)
    currency = Column(String, default="INR")


class ParkingAvailability(Base):
    """
    Stores current availability of parking spaces by type and floor.
    Example: Floor 1, Standard -> 45 total, 12 available
    """

    __tablename__ = "parking_availability"

    id = Column(Integer, primary_key=True)
    floor = Column(Integer, nullable=False)
    space_type = Column(String, nullable=False)  # "standard", "large", "ev", "disabled", "vip"
    total_spaces = Column(Integer, nullable=False)
    available_spaces = Column(Integer, nullable=False)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Reservation(Base):
    """
    Stores parking reservation requests submitted by users.

    Lifecycle: pending → approved OR rejected
    - "pending": User submitted, waiting for admin review
    - "approved": Admin confirmed the reservation
    - "rejected": Admin declined the reservation

    This table is the communication bridge between the user-facing
    chatbot (Stage 1) and the admin agent (Stage 2).
    """

    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=True)  # User's email for notifications
    car_number = Column(String, nullable=False)
    space_type = Column(String, nullable=False)  # standard, large, ev, vip
    start_datetime = Column(String, nullable=False)  # "2026-05-10 09:00"
    end_datetime = Column(String, nullable=False)  # "2026-05-10 18:00"
    status = Column(String, default="pending")  # pending, approved, rejected
    admin_notes = Column(String, nullable=True)  # Reason for rejection, etc.
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
    approved_at = Column(DateTime, nullable=True)


# ========================
# DATABASE MANAGER CLASS
# ========================


class SQLStore:
    """
    Manages the SQL database for dynamic parking data.

    Provides methods to:
    - Initialize the database with default data
    - Query working hours, prices, and availability
    - Update dynamic values (e.g., when a car parks/leaves)
    """

    def __init__(self, database_url: str = None):
        """
        Initialize the SQL database connection.

        Args:
            database_url: SQLAlchemy connection string.
                         Defaults to SQLite file from settings.
        """
        if database_url is None:
            # Prefer PostgreSQL if DATABASE_URL is configured, else SQLite
            database_url = settings.database_url or settings.sql_database_url

        # Ensure the data directory exists (skip for in-memory / PostgreSQL)
        if "sqlite" in database_url and ":memory:" not in database_url:
            db_path = database_url.replace("sqlite:///", "")
            db_dir = os.path.dirname(db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)

        # Create engine with connection settings appropriate for the DB type
        _pg = database_url.startswith("postgresql") or database_url.startswith("postgres")
        if _pg:
            self.engine = create_engine(
                database_url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                pool_recycle=1800,
                echo=False,
            )
        elif ":memory:" in database_url:
            self.engine = create_engine(
                database_url,
                echo=False,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        else:
            self.engine = create_engine(
                database_url,
                echo=False,
                connect_args={"check_same_thread": False},
            )
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create all tables if they don't exist
        Base.metadata.create_all(self.engine)

        # Migrate existing tables: add columns introduced after initial release
        self._migrate_schema()

    def _migrate_schema(self):
        """Add missing columns to existing tables (lightweight migration).

        For PostgreSQL, Alembic handles schema evolution for new installs.
        However, older databases may still require runtime column additions
        when a table was created before a schema upgrade.
        """
        from sqlalchemy import inspect, text

        inspector = inspect(self.engine)
        if "reservations" in inspector.get_table_names():
            columns = [col["name"] for col in inspector.get_columns("reservations")]
            with self.engine.begin() as conn:
                if "updated_at" not in columns:
                    conn.execute(text("ALTER TABLE reservations ADD COLUMN updated_at TIMESTAMP"))
                if "email" not in columns:
                    conn.execute(text("ALTER TABLE reservations ADD COLUMN email VARCHAR"))

        # Ensure parking_slots has the reservation_id linkage column
        if "parking_slots" in inspector.get_table_names():
            slot_cols = [col["name"] for col in inspector.get_columns("parking_slots")]
            with self.engine.begin() as conn:
                if "reservation_id" not in slot_cols:
                    conn.execute(text("ALTER TABLE parking_slots ADD COLUMN reservation_id INTEGER"))

    def initialize_default_data(self):
        """
        Populate the database with default parking data.
        Call this once when setting up the system.

        If existing pricing data is in USD (legacy), it is automatically
        replaced with the correct INR values to fix the currency bug.
        """
        session = self.SessionLocal()
        try:
            # Detect old USD pricing and force re-seed if present
            std_hourly = session.query(ParkingPrice).filter_by(space_type="standard", duration_type="hourly").first()
            stale_usd = std_hourly is not None and std_hourly.currency == "USD"
            if stale_usd:
                # Clear only pricing + availability (keep hours & reservations)
                session.query(ParkingPrice).delete()
                session.query(ParkingAvailability).delete()
                session.commit()
                print("  ↻ Migrating pricing from USD → INR...")

            # Only initialize if tables are empty (or just cleared above)
            if not stale_usd and session.query(WorkingHours).count() > 0:
                print("Database already initialized.")
                return

            # === Working Hours ===
            working_hours = [
                WorkingHours(day_of_week="Monday", open_time="06:00", close_time="23:00", is_open=True),
                WorkingHours(day_of_week="Tuesday", open_time="06:00", close_time="23:00", is_open=True),
                WorkingHours(day_of_week="Wednesday", open_time="06:00", close_time="23:00", is_open=True),
                WorkingHours(day_of_week="Thursday", open_time="06:00", close_time="23:00", is_open=True),
                WorkingHours(day_of_week="Friday", open_time="06:00", close_time="23:00", is_open=True),
                WorkingHours(day_of_week="Saturday", open_time="07:00", close_time="23:00", is_open=True),
                WorkingHours(day_of_week="Sunday", open_time="08:00", close_time="22:00", is_open=True),
            ]
            session.add_all(working_hours)

            # === Pricing (all in INR ₹) ===
            # Source of truth: parking_info.txt — NEVER show USD conversions.
            prices = [
                # Standard parking
                ParkingPrice(space_type="standard", duration_type="hourly", price=50.00, currency="INR"),
                ParkingPrice(space_type="standard", duration_type="daily", price=350.00, currency="INR"),
                ParkingPrice(space_type="standard", duration_type="monthly", price=4500.00, currency="INR"),
                # Large vehicle
                ParkingPrice(space_type="large", duration_type="hourly", price=80.00, currency="INR"),
                ParkingPrice(space_type="large", duration_type="daily", price=550.00, currency="INR"),
                ParkingPrice(space_type="large", duration_type="monthly", price=7000.00, currency="INR"),
                # Electric vehicle (charging included)
                ParkingPrice(space_type="ev", duration_type="hourly", price=120.00, currency="INR"),
                ParkingPrice(space_type="ev", duration_type="daily", price=800.00, currency="INR"),
                ParkingPrice(space_type="ev", duration_type="monthly", price=9500.00, currency="INR"),
                # VIP Premium
                ParkingPrice(space_type="vip", duration_type="hourly", price=200.00, currency="INR"),
                ParkingPrice(space_type="vip", duration_type="daily", price=1500.00, currency="INR"),
                ParkingPrice(space_type="vip", duration_type="monthly", price=18000.00, currency="INR"),
                # Disabled spaces
                ParkingPrice(space_type="disabled", duration_type="hourly", price=30.00, currency="INR"),
                ParkingPrice(space_type="disabled", duration_type="daily", price=120.00, currency="INR"),
                # Bike parking
                ParkingPrice(space_type="bike", duration_type="hourly", price=20.00, currency="INR"),
                ParkingPrice(space_type="bike", duration_type="daily", price=120.00, currency="INR"),
                ParkingPrice(space_type="bike", duration_type="monthly", price=1200.00, currency="INR"),
            ]
            session.add_all(prices)

            # === Availability ===
            # Totals sourced from parking_info.txt (actual ParkSmart HITEC City data).
            # available_spaces starts at total — updated on each admin approval.
            availability = [
                # Ground Floor – VIP (10) + Disabled (10) + Bike (40)
                ParkingAvailability(floor=0, space_type="vip", total_spaces=10, available_spaces=10),
                ParkingAvailability(floor=0, space_type="disabled", total_spaces=10, available_spaces=10),
                ParkingAvailability(floor=0, space_type="bike", total_spaces=40, available_spaces=40),
                # Floor P1 – Standard (135)
                ParkingAvailability(floor=1, space_type="standard", total_spaces=135, available_spaces=135),
                # Floor P2 – Standard (130) + EV (70)
                ParkingAvailability(floor=2, space_type="standard", total_spaces=130, available_spaces=130),
                ParkingAvailability(floor=2, space_type="ev", total_spaces=70, available_spaces=70),
                # Floor P3 – Standard (135)
                ParkingAvailability(floor=3, space_type="standard", total_spaces=135, available_spaces=135),
                # Floor P4 – Large (120)
                ParkingAvailability(floor=4, space_type="large", total_spaces=120, available_spaces=120),
            ]
            session.add_all(availability)

            session.commit()
            print("✓ Database initialized with default parking data.")

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_working_hours(self) -> List[Dict[str, Any]]:
        """
        Get working hours for all days.

        Returns:
            List of dicts with day, open_time, close_time, is_open
        """
        session = self.SessionLocal()
        try:
            hours = session.query(WorkingHours).all()
            return [
                {
                    "day": h.day_of_week,
                    "open_time": h.open_time,
                    "close_time": h.close_time,
                    "is_open": h.is_open,
                }
                for h in hours
            ]
        finally:
            session.close()

    def get_prices(self, space_type: str = None) -> List[Dict[str, Any]]:
        """
        Get parking prices, optionally filtered by space type.

        Args:
            space_type: Filter by type (e.g., "standard", "large", "ev", "vip")

        Returns:
            List of dicts with space_type, duration_type, price, currency
        """
        session = self.SessionLocal()
        try:
            query = session.query(ParkingPrice)
            if space_type:
                query = query.filter(ParkingPrice.space_type == space_type.lower())
            prices = query.all()
            return [
                {
                    "space_type": p.space_type,
                    "duration_type": p.duration_type,
                    "price": p.price,
                    "currency": p.currency,
                }
                for p in prices
            ]
        finally:
            session.close()

    def get_availability(self, space_type: str = None, floor: int = None) -> List[Dict[str, Any]]:
        """
        Get parking space availability.

        Args:
            space_type: Filter by space type
            floor: Filter by floor number

        Returns:
            List of dicts with floor, space_type, total_spaces, available_spaces
        """
        session = self.SessionLocal()
        try:
            query = session.query(ParkingAvailability)
            if space_type:
                query = query.filter(ParkingAvailability.space_type == space_type.lower())
            if floor:
                query = query.filter(ParkingAvailability.floor == floor)
            availability = query.all()
            return [
                {
                    "floor": a.floor,
                    "space_type": a.space_type,
                    "total_spaces": a.total_spaces,
                    "available_spaces": a.available_spaces,
                    "last_updated": a.last_updated.isoformat() if a.last_updated else None,
                }
                for a in availability
            ]
        finally:
            session.close()

    def get_total_availability(self) -> Dict[str, Any]:
        """
        Get a summary of total available spaces for all parking types.

        Reads from the PRODUCTION parking_types / parking_slots tables
        (single source of truth for live availability).  Falls back to the
        legacy parking_availability table only when the production table is
        empty (e.g. seed was never run).

        Returns:
            Dict: space_type_slug -> {"available": int, "total": int,
                                       "reserved": int, "occupied": int}
        """
        try:
            from sqlalchemy import func as _func
            from src.database.session import db_session
            from src.models.parking_slot import ParkingSlot
            from src.models.parking_type import ParkingType

            with db_session() as db:
                types = db.query(ParkingType).all()
                if types:
                    result: Dict[str, Any] = {}
                    for pt in types:
                        # Count actual slot statuses for accuracy
                        rows = (
                            db.query(ParkingSlot.status, _func.count(ParkingSlot.id))
                            .filter(ParkingSlot.parking_type_id == pt.id)
                            .group_by(ParkingSlot.status)
                            .all()
                        )
                        status_map = {s: c for s, c in rows}
                        result[pt.slug] = {
                            "available": status_map.get("available", 0),
                            "total": pt.total_slots,
                            "reserved": status_map.get("reserved", 0),
                            "occupied": status_map.get("occupied", 0),
                        }
                    return result
        except Exception:
            pass  # fall through to legacy table

        # Legacy fallback (parking_availability table)
        session = self.SessionLocal()
        try:
            from sqlalchemy import func

            results = (
                session.query(
                    ParkingAvailability.space_type,
                    func.sum(ParkingAvailability.available_spaces).label("available"),
                    func.sum(ParkingAvailability.total_spaces).label("total"),
                )
                .group_by(ParkingAvailability.space_type)
                .all()
            )
            return {r.space_type: {"available": int(r.available), "total": int(r.total)} for r in results}
        finally:
            session.close()

    def get_dynamic_context(self) -> str:
        """
        Generate a formatted string of all dynamic data for the RAG context.
        This is injected into the LLM prompt alongside vector search results.

        Returns:
            Formatted string with hours, prices, and availability
        """
        hours = self.get_working_hours()
        prices = self.get_prices()
        availability = self.get_total_availability()

        context_parts = []

        # Working Hours
        context_parts.append("=== WORKING HOURS ===")
        for h in hours:
            status = "Open" if h["is_open"] else "Closed"
            context_parts.append(f"{h['day']}: {h['open_time']} - {h['close_time']} ({status})")

        # Prices (INR ₹ — never USD)
        context_parts.append("\n=== PARKING PRICES (INR) ===")
        for p in prices:
            context_parts.append(f"{p['space_type'].title()} ({p['duration_type']}): ₹{p['price']:,.0f}")

        # Availability
        context_parts.append("\n=== CURRENT AVAILABILITY ===")
        for space_type, counts in availability.items():
            context_parts.append(f"{space_type.title()}: {counts['available']} / {counts['total']} spaces available")

        return "\n".join(context_parts)

    # ========================
    # RESERVATION METHODS
    # ========================

    def save_reservation(self, reservation_data: Dict[str, Any]) -> int:
        """
        Save a new reservation to the database with status='pending'.

        Called by the chatbot when a user confirms their reservation details.
        The reservation stays 'pending' until an admin approves or rejects it.

        Args:
            reservation_data: Dict with first_name, last_name, email, car_number,
                            space_type, start_datetime, end_datetime

        Returns:
            The auto-generated ID of the new reservation
        """
        session = self.SessionLocal()
        try:
            reservation = Reservation(
                first_name=reservation_data["first_name"],
                last_name=reservation_data["last_name"],
                email=reservation_data.get("email"),
                car_number=reservation_data["car_number"],
                space_type=reservation_data["space_type"],
                start_datetime=reservation_data["start_datetime"],
                end_datetime=reservation_data["end_datetime"],
                status="pending",
            )
            session.add(reservation)
            session.commit()
            reservation_id = reservation.id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

        # Pre-reserve a physical slot so pending bookings reduce live availability.
        # This runs in the production session (parking_types / parking_slots tables).
        space_type = reservation_data.get("space_type", "")
        if space_type:
            self._reserve_slot_for_pending(reservation_id, space_type)

        return reservation_id

    def _reserve_slot_for_pending(self, reservation_id: int, space_type: str) -> bool:
        """
        Find the first available slot for *space_type*, mark it 'reserved',
        link it to this legacy reservation, and decrement the counter.

        Returns True on success, False if no slot available or on any error.
        Errors are non-fatal — the reservation is still created.

        NOTE: skip_locked=True is NOT used because SQLite raises CompileError for it.
        For SQLite, plain .first() is sufficient (single-writer model).
        For PostgreSQL deployments, add row-level locking at the DB level.
        """
        try:
            from src.database.session import db_session
            from src.models.parking_slot import ParkingSlot, SLOT_STATUS_AVAILABLE, SLOT_STATUS_RESERVED
            from src.models.parking_type import ParkingType

            with db_session() as db:
                pt = db.query(ParkingType).filter_by(slug=space_type.lower()).first()
                if not pt:
                    return False  # Unknown type
                if pt.available_slots <= 0:
                    return False  # No slots — booking should have been blocked upstream

                # Find first available physical slot (no FOR UPDATE — SQLite not supported)
                slot = (
                    db.query(ParkingSlot)
                    .filter_by(parking_type_id=pt.id, status=SLOT_STATUS_AVAILABLE)
                    .first()
                )
                if not slot:
                    # Counter says available but no physical slot — sync counter down
                    pt.available_slots = 0
                    return False

                slot.status = SLOT_STATUS_RESERVED
                slot.reservation_id = reservation_id
                pt.available_slots = max(0, pt.available_slots - 1)

            return True
        except Exception as exc:
            # Non-fatal — reservation is already saved
            import logging as _logging
            _logging.getLogger(__name__).warning(
                "_reserve_slot_for_pending failed for reservation %d (%s): %s",
                reservation_id, space_type, exc,
            )
            return False

    def release_reserved_slot(self, reservation_id: int) -> bool:
        """
        Release the slot that was pre-reserved for *reservation_id*.
        Called on admin rejection or user cancellation.
        Changes slot status 'reserved' → 'available' and increments counter.
        """
        try:
            from src.database.session import db_session
            from src.models.parking_slot import ParkingSlot, SLOT_STATUS_AVAILABLE, SLOT_STATUS_RESERVED
            from src.models.parking_type import ParkingType
            import logging as _logging
            _rlog = _logging.getLogger(__name__)

            with db_session() as db:
                slot = db.query(ParkingSlot).filter_by(
                    reservation_id=reservation_id, status=SLOT_STATUS_RESERVED
                ).first()
                if not slot:
                    return False

                pt = db.query(ParkingType).filter_by(id=slot.parking_type_id).first()
                _rlog.info(
                    "Releasing slot %s from reservation #%d",
                    slot.slot_number, reservation_id,
                )
                slot.status = SLOT_STATUS_AVAILABLE
                slot.reservation_id = None
                if pt:
                    old_count = pt.available_slots
                    # Guard: never exceed total_slots
                    pt.available_slots = min(pt.total_slots, old_count + 1)
                    _rlog.info(
                        "%s available_slots updated: %d \u2192 %d",
                        pt.slug.upper(), old_count, pt.available_slots,
                    )

            return True
        except Exception as exc:
            import logging as _logging
            _logging.getLogger(__name__).warning(
                "release_reserved_slot failed for reservation %d: %s", reservation_id, exc
            )
            return False

    def occupy_reserved_slot(self, reservation_id: int) -> Optional[str]:
        """
        Transition the slot pre-reserved for *reservation_id* from
        'reserved' → 'occupied'. Counter was already decremented at
        reservation creation, so no counter change here.

        Returns the slot_number string, or None if not found.
        """
        try:
            from src.database.session import db_session
            from src.models.parking_slot import ParkingSlot, SLOT_STATUS_OCCUPIED, SLOT_STATUS_RESERVED

            with db_session() as db:
                slot = db.query(ParkingSlot).filter_by(
                    reservation_id=reservation_id, status=SLOT_STATUS_RESERVED
                ).first()
                if not slot:
                    return None

                slot.status = SLOT_STATUS_OCCUPIED
                slot.reservation_id = None  # Clear the pending link
                # current_booking_id stays NULL for legacy reservations (no Booking row)

            return slot.slot_number
        except Exception as exc:
            import logging as _logging
            _logging.getLogger(__name__).warning(
                "occupy_reserved_slot failed for reservation %d: %s", reservation_id, exc
            )
            return None

    def get_reservations(self, status: str = None) -> List[Dict[str, Any]]:
        """
        Retrieve reservations, optionally filtered by status.

        Used by the admin agent to view pending/approved/rejected reservations.

        Args:
            status: Filter by 'pending', 'approved', or 'rejected'.
                    If None, returns all reservations.

        Returns:
            List of reservation dicts ordered by creation time (newest first)
        """
        session = self.SessionLocal()
        try:
            query = session.query(Reservation)
            if status:
                query = query.filter(Reservation.status == status)
            reservations = query.order_by(Reservation.created_at.desc()).all()
            return [
                {
                    "id": r.id,
                    "first_name": r.first_name,
                    "last_name": r.last_name,
                    "email": r.email,
                    "car_number": r.car_number,
                    "space_type": r.space_type,
                    "start_datetime": r.start_datetime,
                    "end_datetime": r.end_datetime,
                    "status": r.status,
                    "admin_notes": r.admin_notes,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                    "approved_at": r.approved_at.isoformat() if r.approved_at else None,
                }
                for r in reservations
            ]
        finally:
            session.close()

    def get_reservation_by_id(self, reservation_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a single reservation by its ID.

        Args:
            reservation_id: The reservation ID to look up

        Returns:
            Reservation dict or None if not found
        """
        session = self.SessionLocal()
        try:
            r = session.query(Reservation).filter(Reservation.id == reservation_id).first()
            if not r:
                return None
            return {
                "id": r.id,
                "first_name": r.first_name,
                "last_name": r.last_name,
                "email": r.email,
                "car_number": r.car_number,
                "space_type": r.space_type,
                "start_datetime": r.start_datetime,
                "end_datetime": r.end_datetime,
                "status": r.status,
                "admin_notes": r.admin_notes,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                "approved_at": r.approved_at.isoformat() if r.approved_at else None,
            }
        finally:
            session.close()

    # ========================
    # REAL-TIME SLOT MANAGEMENT
    # ========================

    def check_availability(self, space_type: str) -> Dict[str, Any]:
        """
        Check current slot availability for a parking type.

        Returns a dict with:
          available  – slots currently free
          total      – total slots of this type
          is_available – True if at least one slot is open
          percentage – availability as 0–100 int
        """
        session = self.SessionLocal()
        try:
            from sqlalchemy import func

            row = (
                session.query(
                    func.sum(ParkingAvailability.available_spaces).label("available"),
                    func.sum(ParkingAvailability.total_spaces).label("total"),
                )
                .filter(ParkingAvailability.space_type == space_type.lower())
                .first()
            )
            available = int(row.available or 0)
            total = int(row.total or 0)
            return {
                "space_type": space_type.lower(),
                "available": available,
                "total": total,
                "is_available": available > 0,
                "percentage": round((available / total) * 100) if total else 0,
            }
        finally:
            session.close()

    def update_availability(self, space_type: str, delta: int) -> bool:
        """
        Adjust available_spaces for a parking type by *delta*.

        Called with delta=-1 on admin approval and delta=+1 on
        reservation cancellation / expiry.

        Updates the first matching row for the type (lowest floor first).
        Returns True on success, False if no matching row exists.
        """
        session = self.SessionLocal()
        try:
            row = (
                session.query(ParkingAvailability)
                .filter(ParkingAvailability.space_type == space_type.lower())
                .order_by(ParkingAvailability.floor)
                .first()
            )
            if not row:
                return False
            row.available_spaces = max(0, min(row.total_spaces, row.available_spaces + delta))
            row.last_updated = datetime.now(timezone.utc)
            session.commit()
            return True
        except Exception as exc:
            session.rollback()
            raise exc
        finally:
            session.close()

    def calculate_price(self, space_type: str, start_dt: str, end_dt: str) -> Tuple[float, str, float]:
        """
        Calculate the INR cost for a booking.

        Pricing tiers (chosen automatically based on duration):
          < 24 hours → hourly rate × ceil(hours)  (min 1 hour)
          >= 24 hours but < 30 days → daily rate × ceil(days)
          >= 30 days → monthly rate × ceil(months)

        Args:
            space_type: "standard" | "large" | "ev" | "vip" | ...
            start_dt:   "YYYY-MM-DD HH:MM"
            end_dt:     "YYYY-MM-DD HH:MM"

        Returns:
            (total_inr, duration_label, unit_price)
            e.g. (400.0, "2 hours @ ₹200/hr", 200.0)
        """
        fmt = "%Y-%m-%d %H:%M"
        try:
            start = datetime.strptime(start_dt, fmt)
            end = datetime.strptime(end_dt, fmt)
        except ValueError:
            # Fallback for datetimes with seconds
            fmt2 = "%Y-%m-%d %H:%M:%S"
            start = datetime.strptime(start_dt[:16], "%Y-%m-%d %H:%M")
            end = datetime.strptime(end_dt[:16], "%Y-%m-%d %H:%M")

        delta = end - start
        total_seconds = max(delta.total_seconds(), 3600)  # minimum 1 hour
        total_hours = total_seconds / 3600
        total_days = total_hours / 24

        prices = self.get_prices(space_type=space_type)
        price_map = {p["duration_type"]: p["price"] for p in prices}

        if total_days >= 30 and "monthly" in price_map:
            months = math.ceil(total_days / 30)
            unit = price_map["monthly"]
            total = months * unit
            label = f"{months} month{'s' if months > 1 else ''} @ ₹{unit:,.0f}/month"
        elif total_hours > 24 and "daily" in price_map:
            days = math.ceil(total_days)
            unit = price_map["daily"]
            total = days * unit
            label = f"{days} day{'s' if days > 1 else ''} @ ₹{unit:,.0f}/day"
        else:
            hours = math.ceil(total_hours)
            unit = price_map.get("hourly", 0)
            total = hours * unit
            label = f"{hours} hour{'s' if hours > 1 else ''} @ ₹{unit:,.0f}/hr"

        return total, label, unit

    def update_reservation_status(self, reservation_id: int, status: str, admin_notes: str = None) -> bool:
        """
        Update a reservation's status (approve or reject).

        Called by the admin agent when the administrator makes a decision.

        Args:
            reservation_id: The ID of the reservation to update
            status: New status — 'approved' or 'rejected'
            admin_notes: Optional notes from admin (e.g., rejection reason)

        Returns:
            True if updated successfully, False if reservation not found
        """
        session = self.SessionLocal()
        try:
            reservation = session.query(Reservation).filter(Reservation.id == reservation_id).first()
            if not reservation:
                return False
            reservation.status = status
            reservation.admin_notes = admin_notes
            reservation.updated_at = datetime.now(timezone.utc)
            if status == "approved":
                reservation.approved_at = datetime.now(timezone.utc)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
