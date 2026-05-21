"""
Tests for PricingService – pure INR pricing with no DB required.

Uses PricingService.quick_estimate() for fully isolated unit tests,
and PricingService.calculate_from_type() with a mock ParkingType object
for integration-level tests.
"""

import pytest
from unittest.mock import MagicMock
from decimal import Decimal
from datetime import datetime

from src.services.pricing_service import PricingService, PriceBreakdown


def make_parking_type(slug="standard", hourly=50, daily=350, monthly=4500):
    """Create a mock ParkingType with INR prices."""
    pt = MagicMock()
    pt.slug = slug
    pt.hourly_price = Decimal(str(hourly))
    pt.daily_price = Decimal(str(daily)) if daily else None
    pt.monthly_price = Decimal(str(monthly)) if monthly else None
    return pt


class TestPricingServiceQuickEstimate:
    """Unit tests using the stateless quick_estimate helper."""

    def test_hourly_2hours(self):
        bd = PricingService.quick_estimate(
            hourly_price=200,
            start="2026-06-01 09:00",
            end="2026-06-01 11:00",
            slug="vip",
        )
        assert bd.total_inr == 400.0
        assert bd.unit_price == 200
        assert "2 hour" in bd.duration_label
        assert bd.currency == "INR"
        assert bd.formatted == "₹400"

    def test_hourly_minimum_1_hour(self):
        """Duration < 1 h should be treated as 1 h."""
        bd = PricingService.quick_estimate(
            hourly_price=50,
            start="2026-06-01 09:00",
            end="2026-06-01 09:30",  # only 30 min
        )
        assert bd.total_inr == 50.0  # 1 hr minimum

    def test_8_hours_standard(self):
        bd = PricingService.quick_estimate(
            hourly_price=50,
            start="2026-06-01 09:00",
            end="2026-06-01 17:00",
        )
        assert bd.total_inr == 400.0  # 8 × 50
        assert "8 hour" in bd.duration_label

    def test_daily_tier_3_days_ev(self):
        bd = PricingService.quick_estimate(
            hourly_price=120,
            start="2026-06-01 09:00",
            end="2026-06-04 09:00",  # 3 days
            daily_price=800,
            monthly_price=9500,
        )
        assert bd.total_inr == 2400.0  # 3 × 800
        assert "3 day" in bd.duration_label

    def test_monthly_tier(self):
        bd = PricingService.quick_estimate(
            hourly_price=200,
            start="2026-06-01 09:00",
            end="2026-07-01 09:00",  # 30 days
            daily_price=1500,
            monthly_price=18000,
        )
        assert bd.total_inr == 18000.0
        assert "month" in bd.duration_label

    def test_no_usd_in_output(self):
        bd = PricingService.quick_estimate(
            hourly_price=80,
            start="2026-06-01 09:00",
            end="2026-06-01 11:00",
        )
        assert "$" not in bd.duration_label
        assert "USD" not in bd.currency
        assert bd.currency == "INR"

    def test_fractional_hours_ceil(self):
        """2.5 hours should be charged as 3 hours."""
        bd = PricingService.quick_estimate(
            hourly_price=50,
            start="2026-06-01 09:00",
            end="2026-06-01 11:30",
        )
        assert bd.total_inr == 150.0  # ceil(2.5) = 3 × 50


class TestPricingServiceCalculateFromType:
    """Tests using a mock ParkingType object."""

    def setup_method(self):
        self.svc = PricingService()

    def test_vip_2hours(self):
        pt = make_parking_type("vip", 200, 1500, 18000)
        bd = self.svc.calculate_from_type(pt, "2026-06-01 10:00", "2026-06-01 12:00")
        assert bd.total_inr == 400.0
        assert bd.space_type == "vip"

    def test_standard_daily(self):
        pt = make_parking_type("standard", 50, 350, 4500)
        bd = self.svc.calculate_from_type(pt, "2026-06-01 09:00", "2026-06-02 09:00")
        # exactly 24 hours → 1 day at daily rate
        assert bd.total_inr == 350.0
        assert "day" in bd.duration_label

    def test_end_before_start_raises(self):
        pt = make_parking_type()
        with pytest.raises(ValueError, match="end time must be after"):
            self.svc.calculate_from_type(pt, "2026-06-01 12:00", "2026-06-01 09:00")

    def test_to_dict_keys(self):
        pt = make_parking_type()
        bd = self.svc.calculate_from_type(pt, "2026-06-01 09:00", "2026-06-01 11:00")
        d = bd.to_dict()
        assert "total_inr" in d
        assert "duration_label" in d
        assert "currency" in d
        assert "formatted" in d
        assert d["currency"] == "INR"
