"""
PricingService – pure INR pricing calculation with no USD conversion.

Pricing tiers (auto-selected by duration):
  < 24 hours   → hourly_price × ceil(hours)  (minimum 1 hour)
  1-29 days    → daily_price  × ceil(days)
  >= 30 days   → monthly_price × ceil(months)

All amounts are in Indian Rupees (₹). USD is never referenced.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from src.models.parking_type import ParkingType
from src.repositories.parking_repository import ParkingRepository

_repo = ParkingRepository()


@dataclass
class PriceBreakdown:
    """Result of a price calculation."""

    space_type: str
    total_inr: float
    unit_price: float
    duration_label: str
    duration_hours: float
    currency: str = "INR"

    @property
    def formatted(self) -> str:
        return f"₹{self.total_inr:,.0f}"

    def to_dict(self) -> dict:
        return {
            "space_type": self.space_type,
            "total_inr": self.total_inr,
            "unit_price": self.unit_price,
            "duration_label": self.duration_label,
            "duration_hours": self.duration_hours,
            "currency": self.currency,
            "formatted": self.formatted,
        }


_DT_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
]


def _parse_dt(value: str | datetime) -> datetime:
    """Accept a datetime object or any common ISO-like string."""
    if isinstance(value, datetime):
        return value
    for fmt in _DT_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    # Last resort: truncate to 16 chars ("YYYY-MM-DD HH:MM") and try again
    if len(value) > 16:
        try:
            return datetime.strptime(value[:16], "%Y-%m-%d %H:%M")
        except ValueError:
            pass
    raise ValueError(f"Cannot parse datetime: {value!r}")


class PricingService:
    """Calculate INR booking costs from a ParkingType and time window."""

    # ------------------------------------------------------------------
    # Database-backed calculation (uses live prices from parking_types)
    # ------------------------------------------------------------------

    def calculate(
        self,
        db: Session,
        parking_type_slug: str,
        start: str | datetime,
        end: str | datetime,
    ) -> PriceBreakdown:
        """
        Calculate the total INR cost for a booking.

        Args:
            db: SQLAlchemy session
            parking_type_slug: "standard", "vip", etc.
            start: booking start (datetime or string)
            end:   booking end   (datetime or string)

        Raises:
            ValueError: if the parking type is unknown or times are invalid
        """
        pt = _repo.get_by_slug(db, parking_type_slug)
        if pt is None:
            raise ValueError(f"Unknown parking type: {parking_type_slug!r}")
        return self._calculate_from_type(pt, start, end)

    def calculate_from_type(
        self,
        parking_type: ParkingType,
        start: str | datetime,
        end: str | datetime,
    ) -> PriceBreakdown:
        return self._calculate_from_type(parking_type, start, end)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _calculate_from_type(
        self,
        pt: ParkingType,
        start: str | datetime,
        end: str | datetime,
    ) -> PriceBreakdown:
        start_dt = _parse_dt(start)
        end_dt = _parse_dt(end)

        if end_dt <= start_dt:
            raise ValueError("end time must be after start time")

        delta_seconds = (end_dt - start_dt).total_seconds()
        total_hours = max(delta_seconds / 3600, 1.0)  # min 1 hour
        total_days = total_hours / 24

        hourly = float(pt.hourly_price) if pt.hourly_price else 0.0
        daily = float(pt.daily_price) if pt.daily_price else hourly * 24
        monthly = float(pt.monthly_price) if pt.monthly_price else daily * 30

        if total_days >= 30 and pt.monthly_price:
            months = math.ceil(total_days / 30)
            unit = monthly
            total = months * unit
            label = f"{months} month{'s' if months > 1 else ''} @ ₹{unit:,.0f}/month"
        elif total_hours >= 24 and pt.daily_price:
            days = math.ceil(total_days)
            unit = daily
            total = days * unit
            label = f"{days} day{'s' if days > 1 else ''} @ ₹{unit:,.0f}/day"
        else:
            hours = math.ceil(total_hours)
            unit = hourly
            total = hours * unit
            label = f"{hours} hour{'s' if hours > 1 else ''} @ ₹{unit:,.0f}/hr"

        return PriceBreakdown(
            space_type=pt.slug,
            total_inr=round(total, 2),
            unit_price=unit,
            duration_label=label,
            duration_hours=total_hours,
        )

    # ------------------------------------------------------------------
    # Stateless helper (no DB needed, uses explicit prices)
    # ------------------------------------------------------------------

    @staticmethod
    def quick_estimate(
        hourly_price: float,
        start: str | datetime,
        end: str | datetime,
        daily_price: Optional[float] = None,
        monthly_price: Optional[float] = None,
        slug: str = "unknown",
    ) -> PriceBreakdown:
        """
        Fast calculation without hitting the DB.
        Useful for chatbot responses where we already have the price.
        """
        start_dt = _parse_dt(start)
        end_dt = _parse_dt(end)
        delta_seconds = max((end_dt - start_dt).total_seconds(), 3600)
        total_hours = delta_seconds / 3600
        total_days = total_hours / 24

        if monthly_price and total_days >= 30:
            months = math.ceil(total_days / 30)
            total = months * monthly_price
            label = f"{months} month{'s' if months > 1 else ''} @ ₹{monthly_price:,.0f}/month"
            unit = monthly_price
        elif daily_price and total_hours > 24:
            days = math.ceil(total_days)
            total = days * daily_price
            label = f"{days} day{'s' if days > 1 else ''} @ ₹{daily_price:,.0f}/day"
            unit = daily_price
        else:
            hours = math.ceil(total_hours)
            total = hours * hourly_price
            label = f"{hours} hour{'s' if hours > 1 else ''} @ ₹{hourly_price:,.0f}/hr"
            unit = hourly_price

        return PriceBreakdown(
            space_type=slug,
            total_inr=round(total, 2),
            unit_price=unit,
            duration_label=label,
            duration_hours=total_hours,
        )
