"""
src/services/parking_information_service.py
===========================================
Single source of truth for live parking data.

All pricing, slot counts, availability, and feature information is fetched
directly from the parking_types / parking_slots tables here — never from
any hardcoded text file or legacy table.

Used by:
  - RAGChain (dynamic_context injection in prompts)
  - API endpoints (/api/parking/types, /api/admin/dashboard)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class ParkingInformationService:
    """
    Provides live, DB-sourced parking information for use in chatbot prompts,
    API responses, and admin dashboards.

    All methods accept a SQLAlchemy Session so callers control the transaction.
    """

    # ──────────────────────────────────────────────────────────────────────
    # Public read helpers
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def get_live_parking_types(db: "Session") -> list[dict]:
        """Return all active parking types with full live slot stats."""
        from sqlalchemy import case, func, select

        from src.models.parking_slot import ParkingSlot
        from src.models.parking_type import ParkingType

        rows = db.execute(
            select(ParkingType)
            .where(ParkingType.is_active.is_(True))
            .order_by(ParkingType.id)
        ).scalars().all()

        result = []
        for pt in rows:
            counts = db.execute(
                select(
                    func.count().label("total"),
                    func.sum(
                        case((ParkingSlot.status == "available", 1), else_=0)
                    ).label("available"),
                    func.sum(
                        case((ParkingSlot.status == "occupied", 1), else_=0)
                    ).label("occupied"),
                    func.sum(
                        case((ParkingSlot.status == "maintenance", 1), else_=0)
                    ).label("maintenance"),
                ).where(ParkingSlot.parking_type_id == pt.id)
            ).first()

            result.append(
                {
                    "id": pt.id,
                    "slug": pt.slug,
                    "name": pt.name,
                    "description": pt.description,
                    "hourly_price": float(pt.hourly_price) if pt.hourly_price else 0.0,
                    "daily_price": float(pt.daily_price) if pt.daily_price else 0.0,
                    "monthly_price": (
                        float(pt.monthly_price) if pt.monthly_price else None
                    ),
                    "features": pt.features or [],
                    "is_active": pt.is_active,
                    "total_slots": counts.total or 0,
                    "available_slots": counts.available or 0,
                    "occupied_slots": counts.occupied or 0,
                    "maintenance_slots": counts.maintenance or 0,
                    "availability_status": pt.availability_status,
                    "availability_percentage": pt.availability_percentage,
                }
            )
        return result

    @staticmethod
    def get_live_availability(db: "Session") -> str:
        """
        Return a human-readable availability summary for chatbot prompts.

        Example output:
          Standard Parking: 399/400 slots — AVAILABLE
          VIP Premium: 0/10 slots — FULL
        """
        types = ParkingInformationService.get_live_parking_types(db)
        if not types:
            return "No parking type data available."

        lines = []
        for t in types:
            pct = t["availability_percentage"]
            avail = t["available_slots"]
            total = t["total_slots"]

            if avail == 0:
                status = "FULL ❌"
            elif pct < 20:
                status = "LIMITED ⚠️"
            else:
                status = "AVAILABLE ✅"

            lines.append(
                f"  • {t['name']}: {avail}/{total} slots — {status}"
            )
        return "\n".join(lines)

    @staticmethod
    def get_live_pricing(db: "Session") -> str:
        """
        Return a human-readable pricing table for chatbot prompts.

        Example output:
          Standard Parking: ₹50/hr | ₹350/day | ₹4,500/month
        """
        types = ParkingInformationService.get_live_parking_types(db)
        if not types:
            return "Pricing data unavailable."

        lines = []
        for t in types:
            monthly = (
                f"₹{t['monthly_price']:,.0f}/month"
                if t["monthly_price"]
                else "no monthly plan"
            )
            lines.append(
                f"  • {t['name']}: "
                f"₹{t['hourly_price']:,.0f}/hr | "
                f"₹{t['daily_price']:,.0f}/day | "
                f"{monthly}"
            )
        return "\n".join(lines)

    @staticmethod
    def get_parking_features(db: "Session") -> str:
        """
        Return per-type feature lists for chatbot prompts.
        """
        types = ParkingInformationService.get_live_parking_types(db)
        if not types:
            return "Feature data unavailable."

        lines = []
        for t in types:
            feats = ", ".join(t["features"]) if t["features"] else "—"
            lines.append(f"  • {t['name']}: {feats}")
        return "\n".join(lines)

    @staticmethod
    def get_full_dynamic_context(db: "Session") -> str:
        """
        Assemble the complete dynamic context block injected into chatbot prompts.

        This is the AUTHORITATIVE source for all operational data.  The static
        parking_info.txt must NOT duplicate any of these values.
        """
        types = ParkingInformationService.get_live_parking_types(db)

        if not types:
            return "⚠️  No live parking data available — database may be empty."

        lines: list[str] = []
        lines.append("════════════════════════════════════════")
        lines.append("  LIVE PARKING DATA  (from database)")
        lines.append("════════════════════════════════════════")

        for t in types:
            avail = t["available_slots"]
            total = t["total_slots"]
            occupied = t["occupied_slots"]
            pct = t["availability_percentage"]

            if avail == 0:
                status_label = "FULL"
            elif pct < 20:
                status_label = "LIMITED"
            else:
                status_label = "AVAILABLE"

            monthly_str = (
                f"₹{t['monthly_price']:,.0f}/month"
                if t["monthly_price"]
                else "no monthly plan"
            )
            feats = ", ".join(t["features"][:4]) if t["features"] else "—"

            lines.append(f"\n[{t['name'].upper()}]  ({t['slug']})")
            lines.append(f"  Availability : {avail}/{total} slots — {status_label}")
            lines.append(f"  Occupied     : {occupied} slots")
            lines.append(
                f"  Pricing      : ₹{t['hourly_price']:,.0f}/hr | "
                f"₹{t['daily_price']:,.0f}/day | {monthly_str}"
            )
            lines.append(f"  Description  : {t['description']}")
            lines.append(f"  Features     : {feats}")
            lines.append(f"  Active       : {'Yes' if t['is_active'] else 'No (closed)'}")

        lines.append("\n════════════════════════════════════════")
        return "\n".join(lines)
