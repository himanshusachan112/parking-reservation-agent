"""
ParkingService – read-only queries about parking types + live availability.

Composes AvailabilityService and PricingService to return frontend-ready
dicts that include pricing, live slot counts, and availability status labels.
"""

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.database.session import db_session
from src.repositories.parking_repository import ParkingRepository
from src.services.availability_service import AvailabilityService
from src.services.pricing_service import PricingService

_repo = ParkingRepository()
_avail_svc = AvailabilityService()
_pricing_svc = PricingService()


class ParkingService:
    """Read-only facade for parking type data consumed by the API and frontend."""

    def get_all_types(self) -> List[Dict]:
        """
        Return all active parking types with live availability and pricing.

        Used by `GET /api/parking/types` (polled every 30 s by ParkingCards).
        """
        with db_session() as db:
            return _avail_svc.get_summary(db)

    def get_type(self, slug: str) -> Optional[Dict]:
        """Return a single parking type by slug."""
        with db_session() as db:
            return _avail_svc.get_for_type(db, slug)

    def get_live_status(self) -> List[Dict]:
        """
        Return availability with colour-coded status.

        Adds `status_colour` = "green" | "yellow" | "red" for frontend badges.
        """
        types = self.get_all_types()
        for t in types:
            pct = t.get("availability_percentage", 0)
            t["status_colour"] = (
                "green" if pct >= 50 else ("yellow" if pct > 0 else "red")
            )
        return types

    def calculate_price(
        self,
        parking_type_slug: str,
        start: str | datetime,
        end: str | datetime,
    ) -> Dict:
        """
        Calculate INR price for a time window.

        Used by `POST /api/parking/calculate-price`.
        """
        with db_session() as db:
            bd = _pricing_svc.calculate(db, parking_type_slug, start, end)
        return bd.to_dict()

    def check_availability(self, slug: str) -> Dict:
        """
        Return availability + alternatives for `POST /api/parking/check-availability`.
        """
        with db_session() as db:
            summary = _avail_svc.get_for_type(db, slug)
            if summary is None:
                return {"error": f"Unknown parking type: {slug}"}
            if not summary["is_available"]:
                summary["alternatives"] = _avail_svc.get_alternatives(db, slug)
            else:
                summary["alternatives"] = []
        return summary
