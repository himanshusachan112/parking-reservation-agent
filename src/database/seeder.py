"""
src/database/seeder.py
======================
Auto-seed helpers used by the FastAPI startup event to populate a fresh
database with parking types and slot rows.

This module lives inside the `src` package so it is always importable on
any deployment platform without sys.path manipulation.
"""

import logging

from src.models.parking_slot import ParkingSlot
from src.models.parking_type import ParkingType

log = logging.getLogger(__name__)

# ── Parking type definitions ──────────────────────────────────────────────────
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
        "features": ["CCTV monitored", "Covered parking", "Elevator access", "Smart slot indicators"],
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
        "features": ["Extra-wide lanes", "High roof clearance (2.5 m)", "Floor P4 dedicated", "Easy maneuvering area"],
    },
    {
        "slug": "ev",
        "name": "EV Charging",
        "description": (
            "Dedicated electric vehicle zone on floor P2. "
            "Level 2 AC chargers and DC fast-charge ports — charging included in fee. "
            "Supports Tata EV, MG ZS EV, Tesla, BYD, Ather, Ola Electric and all CCS2/Type-2 vehicles."
        ),
        "total_slots": 70,
        "hourly_price": 120.00,
        "daily_price": 800.00,
        "monthly_price": 9500.00,
        "features": ["Charging included in fee", "DC fast-charge + Level 2 AC", "Floor P2 — EV Zone", "24/7 charging access"],
    },
    {
        "slug": "vip",
        "name": "VIP Premium",
        "description": (
            "Exclusive premium covered spots on the ground floor, "
            "closest to the main entrance. Includes dedicated valet support."
        ),
        "total_slots": 10,
        "hourly_price": 200.00,
        "daily_price": 1500.00,
        "monthly_price": 18000.00,
        "features": ["Covered premium area", "Closest to main exit", "Dedicated valet support", "High-security monitoring"],
    },
    {
        "slug": "disabled",
        "name": "Disabled / Accessible",
        "description": (
            "Wheelchair-accessible bays located near elevators on the ground floor. "
            "Requires a valid disability permit."
        ),
        "total_slots": 10,
        "hourly_price": 30.00,
        "daily_price": 120.00,
        "monthly_price": None,
        "features": ["Wheelchair accessible", "Extra-wide bays", "Elevator priority", "Ground floor — near entry"],
    },
    {
        "slug": "bike",
        "name": "Bike / 2-Wheeler",
        "description": (
            "Covered ground-floor zone for motorcycles, scooters & electric two-wheelers. "
            "Includes helmet safety lockers and EV charging points for e-bikes."
        ),
        "total_slots": 40,
        "hourly_price": 20.00,
        "daily_price": 120.00,
        "monthly_price": 1200.00,
        "features": ["Covered area", "Helmet lockers", "EV bike charging", "CCTV monitored"],
    },
]

SLOT_CONFIG = {
    "standard": {"prefix": "STD", "floors": ["P1", "P2", "P3"]},
    "large":    {"prefix": "LRG", "floors": ["P4"]},
    "ev":       {"prefix": "EV",  "floors": ["P2"]},
    "vip":      {"prefix": "VIP", "floors": ["Ground"]},
    "disabled": {"prefix": "DIS", "floors": ["Ground"]},
    "bike":     {"prefix": "BKE", "floors": ["Ground"]},
}


def _floor_for_index(floors: list, index: int, total: int) -> str:
    slots_per_floor = max(1, total // len(floors))
    floor_idx = min(index // slots_per_floor, len(floors) - 1)
    return floors[floor_idx]


def seed_parking_types(db) -> dict:
    """Upsert parking type rows. Returns slug → ParkingType mapping."""
    types = {}
    for td in PARKING_TYPES:
        existing = db.query(ParkingType).filter_by(slug=td["slug"]).first()
        if existing:
            for k, v in td.items():
                if k not in ("total_slots", "available_slots"):
                    setattr(existing, k, v)
            pt = existing
        else:
            non_slot = {k: v for k, v in td.items() if k not in ("total_slots", "available_slots")}
            pt = ParkingType(total_slots=0, available_slots=0, **non_slot)
            db.add(pt)
        db.flush()
        types[td["slug"]] = pt
        log.info("  %-10s upserted (₹%g/hr)", td["slug"].upper(), td["hourly_price"])
    return types


def seed_slots(db, types: dict) -> int:
    """Generate individual parking slot rows idempotently. Returns count of new rows."""
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
            for s in db.query(ParkingSlot.slot_number).filter_by(parking_type_id=pt.id).all()
        }

        new_slots = 0
        for i in range(total):
            number = f"{prefix}-{i + 1:03d}"
            if number in existing_numbers:
                continue
            floor = _floor_for_index(floors, i, total)
            db.add(ParkingSlot(
                slot_number=number,
                parking_type_id=pt.id,
                floor_number=floor,
                status="available",
            ))
            new_slots += 1

        # Update counters on the type row
        total_count = len(existing_numbers) + new_slots
        pt.total_slots = total_count
        pt.available_slots = total_count
        created += new_slots
        log.info("  %-10s %d new slots created", slug.upper(), new_slots)

    return created
