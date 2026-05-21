"""
scripts/seed_parking_data.py
============================
Idempotent seed script for the ParkSmart PostgreSQL database.

Run once after `alembic upgrade head`:

    python scripts/seed_parking_data.py

Re-running is safe – existing rows are updated, not duplicated.

Parking data is sourced from the real HITEC City, Hyderabad EPAM campus.
All prices are in Indian Rupees (₹) – no USD.
"""

import logging
import os
import sys

# ── project root on sys.path ────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.base import Base
from src.database.postgres import get_engine, validate_connection
from src.database.session import db_session
from src.models import AdminAction, Booking, ParkingSlot, ParkingType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("seed")

# ── Parking type definitions ─────────────────────────────────────────────────
PARKING_TYPES = [
    {
        "slug": "standard",
        "name": "Standard Parking",
        "description": (
            "Covered bays for hatchbacks, sedans & compact SUVs. "
            "Floors P1, P2 and P3 — CCTV monitored with smart slot-guidance indicators. "
            "Max vehicle size: 5.0 m × 2.0 m × 1.8 m."
        ),
        "total_slots": 400,
        "hourly_price": 50.00,
        "daily_price": 350.00,
        "monthly_price": 4500.00,
        "features": [
            "CCTV monitored",
            "Covered parking",
            "Elevator access",
            "Smart slot indicators",
        ],
    },
    {
        "slug": "large",
        "name": "Large Vehicle",
        "description": (
            "Extra-wide lanes with high roof clearance for large SUVs, MUVs, "
            "pickup trucks, corporate vans & tempo travelers. "
            "Dedicated floor P4 with easy maneuvering area. "
            "Max vehicle size: 6.5 m × 2.5 m × 2.5 m."
        ),
        "total_slots": 120,
        "hourly_price": 80.00,
        "daily_price": 550.00,
        "monthly_price": 7000.00,
        "features": [
            "Extra-wide lanes",
            "High roof clearance (2.5 m)",
            "Floor P4 dedicated",
            "Easy maneuvering area",
        ],
    },
    {
        "slug": "ev",
        "name": "EV Charging",
        "description": (
            "Dedicated electric vehicle zone on floor P2. "
            "Level 2 AC chargers and DC fast-charge ports — charging included in fee. "
            "Supports Tata EV, MG ZS EV, Tesla, BYD, Ather, Ola Electric and all CCS2/Type-2 vehicles. "
            "Smart charging management with real-time battery monitoring."
        ),
        "total_slots": 70,
        "hourly_price": 120.00,
        "daily_price": 800.00,
        "monthly_price": 9500.00,
        "features": [
            "Charging included in fee",
            "DC fast-charge + Level 2 AC",
            "Floor P2 — EV Zone",
            "24/7 charging access",
        ],
    },
    {
        "slug": "vip",
        "name": "VIP Premium",
        "description": (
            "Exclusive premium covered spots on the ground floor, "
            "closest to the main entrance. "
            "Reserved for corporate executives, premium members & invited guests. "
            "Includes dedicated valet support and high-security CCTV monitoring."
        ),
        "total_slots": 10,
        "hourly_price": 200.00,
        "daily_price": 1500.00,
        "monthly_price": 18000.00,
        "features": [
            "Covered premium area",
            "Closest to main exit",
            "Dedicated valet support",
            "High-security monitoring",
        ],
    },
    {
        "slug": "disabled",
        "name": "Disabled / Accessible",
        "description": (
            "Wheelchair-accessible bays located near elevators on the ground floor. "
            "Requires a valid disability permit. "
            "Extra-wide bays with elevator priority access and level entry ramps."
        ),
        "total_slots": 10,
        "hourly_price": 30.00,
        "daily_price": 120.00,
        "monthly_price": None,
        "features": [
            "Wheelchair accessible",
            "Extra-wide bays",
            "Elevator priority",
            "Ground floor — near entry",
        ],
    },
    {
        "slug": "bike",
        "name": "Bike / 2-Wheeler",
        "description": (
            "Covered ground-floor zone for motorcycles, scooters & electric two-wheelers. "
            "Includes helmet safety lockers, EV charging points for e-bikes, and CCTV monitoring."
        ),
        "total_slots": 40,
        "hourly_price": 20.00,
        "daily_price": 120.00,
        "monthly_price": 1200.00,
        "features": [
            "Covered area",
            "Helmet lockers",
            "EV bike charging",
            "CCTV monitored",
        ],
    },
]

# Slot prefix and floor mapping per parking type
SLOT_CONFIG = {
    "standard": {"prefix": "STD", "floors": ["P1", "P2", "P3"]},
    "large": {"prefix": "LRG", "floors": ["P4"]},
    "ev": {"prefix": "EV", "floors": ["P2"]},
    "vip": {"prefix": "VIP", "floors": ["Ground"]},
    "disabled": {"prefix": "DIS", "floors": ["Ground"]},
    "bike": {"prefix": "BKE", "floors": ["Ground"]},
}


def _floor_for_index(floors: list[str], index: int, total: int) -> str:
    """Distribute slots across floors round-robin."""
    slots_per_floor = max(1, total // len(floors))
    floor_idx = min(index // slots_per_floor, len(floors) - 1)
    return floors[floor_idx]


def seed_parking_types(db) -> dict[str, ParkingType]:
    """Upsert parking type rows.  Returns slug → ParkingType mapping.

    IMPORTANT – operational fields total_slots and available_slots are NEVER
    touched on re-runs; they are owned by the admin panel.  On a FRESH install
    (no row exists yet), both start at 0 — the admin must explicitly add slots.
    """
    log.info("━━━ Seeding parking types ━━━")
    types: dict[str, ParkingType] = {}

    for td in PARKING_TYPES:
        existing = db.query(ParkingType).filter_by(slug=td["slug"]).first()
        if existing:
            # Update only non-operational fields (name, description, prices, features).
            # DO NOT touch total_slots or available_slots — those are live operational
            # data that may have been modified by admin actions or active bookings.
            for k, v in td.items():
                if k not in ("total_slots", "available_slots"):
                    setattr(existing, k, v)
            pt = existing
            action = "updated (prices/desc only)"
        else:
            # Fresh install: start with 0 slots — admin configures capacity via the
            # admin panel.  Hardcoded defaults in PARKING_TYPES are intentionally
            # ignored for slot counts so the system boots in a known zero state.
            non_slot_fields = {k: v for k, v in td.items() if k not in ("total_slots", "available_slots")}
            pt = ParkingType(total_slots=0, available_slots=0, **non_slot_fields)
            db.add(pt)
            action = "created (0 slots — configure via admin panel)"

        db.flush()
        types[td["slug"]] = pt
        log.info(
            "  %-10s %s  (₹%g/hr, %d slots)",
            td["slug"].upper(),
            action,
            td["hourly_price"],
            td["total_slots"],
        )

    return types


def seed_slots(db, types: dict[str, ParkingType]) -> int:
    """Generate individual parking slot rows idempotently."""
    log.info("━━━ Seeding parking slots ━━━")
    created = 0

    for td in PARKING_TYPES:
        slug = td["slug"]
        pt = types[slug]
        cfg = SLOT_CONFIG[slug]
        prefix = cfg["prefix"]
        floors = cfg["floors"]
        total = td["total_slots"]

        existing_numbers = {
            s.slot_number
            for s in db.query(ParkingSlot.slot_number)
            .filter_by(parking_type_id=pt.id)
            .all()
        }

        new_slots = 0
        for i in range(total):
            number = f"{prefix}-{i + 1:03d}"
            if number in existing_numbers:
                continue
            floor = _floor_for_index(floors, i, total)
            slot = ParkingSlot(
                slot_number=number,
                parking_type_id=pt.id,
                floor_number=floor,
                status="available",
            )
            db.add(slot)
            new_slots += 1

        log.info(
            "  %-10s %d/%d slots created (floor(s): %s)",
            slug.upper(),
            new_slots,
            total,
            ", ".join(floors),
        )
        created += new_slots

    return created


def verify(db) -> None:
    """Print a summary table to confirm seed data."""
    log.info("━━━ Verification ━━━")
    types = db.query(ParkingType).order_by(ParkingType.id).all()
    log.info(
        "  %-20s  %5s  %5s  %10s  %10s", "TYPE", "TOTAL", "AVAIL", "HRLY ₹", "MONTHLY ₹"
    )
    log.info("  " + "─" * 65)
    for pt in types:
        log.info(
            "  %-20s  %5d  %5d  %10.0f  %10s",
            pt.name,
            pt.total_slots,
            pt.available_slots,
            float(pt.hourly_price),
            f"₹{float(pt.monthly_price):,.0f}" if pt.monthly_price else "—",
        )
    slot_count = db.query(ParkingSlot).count()
    log.info("  ─" * 33)
    log.info("  Total slots in DB: %d", slot_count)


def main() -> None:
    log.info("╔══════════════════════════════════════╗")
    log.info("║  ParkSmart PostgreSQL Seed Script     ║")
    log.info("╚══════════════════════════════════════╝")

    # Validate DB is reachable
    if not validate_connection():
        log.error("Cannot connect to database. Check DATABASE_URL in .env")
        sys.exit(1)

    # Ensure production tables exist (safe to call if Alembic already ran)
    engine = get_engine()
    Base.metadata.create_all(engine)

    with db_session() as db:
        seed_parking_types(db)
        # NOTE: seed_slots() is intentionally NOT called here.
        # Physical slot rows must be added through the admin panel
        # (POST /api/admin/parking-types/{slug}/slots/add).
        # This ensures the system boots with a clean zero-slot state on fresh installs.

    log.info("✓ Seed completed — parking types configured (0 slots; use admin panel to add)")

    # Read-only verification (separate session)
    with db_session() as db:
        verify(db)

    log.info("✓ ParkSmart database is ready.")


if __name__ == "__main__":
    main()
