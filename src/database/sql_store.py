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

import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime
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
    open_time = Column(String, nullable=False)   # "06:00"
    close_time = Column(String, nullable=False)  # "23:00"
    is_open = Column(Boolean, default=True)      # False if closed that day


class ParkingPrice(Base):
    """
    Stores pricing for different parking space types and durations.
    Example: Standard parking -> $3/hour, $15/day
    """
    __tablename__ = "parking_prices"

    id = Column(Integer, primary_key=True)
    space_type = Column(String, nullable=False)    # "standard", "large", "ev", "vip"
    duration_type = Column(String, nullable=False)  # "hourly", "daily", "weekly", "monthly"
    price = Column(Float, nullable=False)           # Price in dollars
    currency = Column(String, default="USD")


class ParkingAvailability(Base):
    """
    Stores current availability of parking spaces by type and floor.
    Example: Floor 1, Standard -> 45 total, 12 available
    """
    __tablename__ = "parking_availability"

    id = Column(Integer, primary_key=True)
    floor = Column(Integer, nullable=False)
    space_type = Column(String, nullable=False)      # "standard", "large", "ev", "disabled", "vip"
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
    email = Column(String, nullable=True)              # User's email for notifications
    car_number = Column(String, nullable=False)
    space_type = Column(String, nullable=False)      # standard, large, ev, vip
    start_datetime = Column(String, nullable=False)   # "2026-05-10 09:00"
    end_datetime = Column(String, nullable=False)     # "2026-05-10 18:00"
    status = Column(String, default="pending")         # pending, approved, rejected
    admin_notes = Column(String, nullable=True)        # Reason for rejection, etc.
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
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
            database_url = settings.sql_database_url

        # Ensure the data directory exists (skip for in-memory databases)
        if "sqlite" in database_url and ":memory:" not in database_url:
            db_path = database_url.replace("sqlite:///", "")
            db_dir = os.path.dirname(db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)

        # Create the database engine and session factory
        # For in-memory SQLite, we use StaticPool to ensure all threads
        # share the same connection (otherwise each thread gets an empty DB).
        # This is critical for FastAPI's TestClient which runs handlers
        # in a thread pool.
        if ":memory:" in database_url:
            self.engine = create_engine(
                database_url,
                echo=False,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        else:
            self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create all tables if they don't exist
        Base.metadata.create_all(self.engine)

    def initialize_default_data(self):
        """
        Populate the database with default parking data.
        Call this once when setting up the system.
        """
        session = self.SessionLocal()
        try:
            # Only initialize if tables are empty
            if session.query(WorkingHours).count() > 0:
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

            # === Pricing ===
            prices = [
                # Standard parking
                ParkingPrice(space_type="standard", duration_type="hourly", price=3.00),
                ParkingPrice(space_type="standard", duration_type="daily", price=15.00),
                ParkingPrice(space_type="standard", duration_type="weekly", price=60.00),
                ParkingPrice(space_type="standard", duration_type="monthly", price=200.00),
                # Large vehicle
                ParkingPrice(space_type="large", duration_type="hourly", price=5.00),
                ParkingPrice(space_type="large", duration_type="daily", price=25.00),
                ParkingPrice(space_type="large", duration_type="weekly", price=100.00),
                ParkingPrice(space_type="large", duration_type="monthly", price=350.00),
                # Electric vehicle
                ParkingPrice(space_type="ev", duration_type="hourly", price=4.00),
                ParkingPrice(space_type="ev", duration_type="daily", price=20.00),
                ParkingPrice(space_type="ev", duration_type="weekly", price=80.00),
                ParkingPrice(space_type="ev", duration_type="monthly", price=280.00),
                # VIP
                ParkingPrice(space_type="vip", duration_type="monthly", price=500.00),
            ]
            session.add_all(prices)

            # === Availability ===
            availability = [
                # Floor 1 - Standard (120) + Disabled (20) + VIP (10)
                ParkingAvailability(floor=1, space_type="standard", total_spaces=120, available_spaces=45),
                ParkingAvailability(floor=1, space_type="disabled", total_spaces=20, available_spaces=15),
                ParkingAvailability(floor=1, space_type="vip", total_spaces=10, available_spaces=3),
                # Floor 2 - Standard (115) + EV (40)
                ParkingAvailability(floor=2, space_type="standard", total_spaces=115, available_spaces=60),
                ParkingAvailability(floor=2, space_type="ev", total_spaces=40, available_spaces=22),
                # Floor 3 - Standard (115)
                ParkingAvailability(floor=3, space_type="standard", total_spaces=115, available_spaces=80),
                # Floor 4 - Large (80)
                ParkingAvailability(floor=4, space_type="large", total_spaces=80, available_spaces=55),
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

    def get_total_availability(self) -> Dict[str, int]:
        """
        Get a summary of total available spaces across all floors.
        
        Returns:
            Dict with space_type -> total available count
        """
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
            return {
                r.space_type: {"available": int(r.available), "total": int(r.total)}
                for r in results
            }
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

        # Prices
        context_parts.append("\n=== PARKING PRICES ===")
        for p in prices:
            context_parts.append(f"{p['space_type'].title()} ({p['duration_type']}): ${p['price']:.2f}")

        # Availability
        context_parts.append("\n=== CURRENT AVAILABILITY ===")
        for space_type, counts in availability.items():
            context_parts.append(
                f"{space_type.title()}: {counts['available']} / {counts['total']} spaces available"
            )

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
            return reservation_id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

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
            r = session.query(Reservation).filter(
                Reservation.id == reservation_id
            ).first()
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
                "approved_at": r.approved_at.isoformat() if r.approved_at else None,
            }
        finally:
            session.close()

    def update_reservation_status(
        self, reservation_id: int, status: str, admin_notes: str = None
    ) -> bool:
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
            reservation = session.query(Reservation).filter(
                Reservation.id == reservation_id
            ).first()
            if not reservation:
                return False
            reservation.status = status
            reservation.admin_notes = admin_notes
            if status == "approved":
                reservation.approved_at = datetime.now(timezone.utc)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
