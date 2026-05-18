"""
Tests for the SQL Store module.

These tests verify that:
1. Database initialization works correctly
2. Working hours, prices, and availability queries work
3. Dynamic context generation produces valid output

Uses an in-memory SQLite database for isolation.
"""

import pytest
from src.database.sql_store import SQLStore, Base


class TestSQLStore:
    """Tests for the SQLStore class."""

    def setup_method(self):
        """Create a fresh in-memory database for each test."""
        # Use in-memory SQLite for test isolation
        self.store = SQLStore(database_url="sqlite:///:memory:")
        self.store.initialize_default_data()

    def test_initialization_creates_data(self):
        """Test that default data is properly initialized."""
        hours = self.store.get_working_hours()
        prices = self.store.get_prices()
        availability = self.store.get_availability()

        # Should have 7 days of working hours
        assert len(hours) == 7

        # Should have multiple price entries
        assert len(prices) > 0

        # Should have availability entries
        assert len(availability) > 0

    def test_get_working_hours(self):
        """Test working hours retrieval."""
        hours = self.store.get_working_hours()

        # Check Monday exists with correct format
        monday = next(h for h in hours if h["day"] == "Monday")
        assert monday["open_time"] == "06:00"
        assert monday["close_time"] == "23:00"
        assert monday["is_open"] is True

    def test_get_prices_all(self):
        """Test retrieving all prices."""
        prices = self.store.get_prices()

        # Should include standard hourly
        standard_hourly = next(
            (p for p in prices if p["space_type"] == "standard" and p["duration_type"] == "hourly"),
            None,
        )
        assert standard_hourly is not None
        assert standard_hourly["price"] == 3.00

    def test_get_prices_filtered(self):
        """Test retrieving prices filtered by space type."""
        ev_prices = self.store.get_prices(space_type="ev")

        # All prices should be for EV type
        assert all(p["space_type"] == "ev" for p in ev_prices)
        assert len(ev_prices) > 0

    def test_get_availability(self):
        """Test availability retrieval."""
        availability = self.store.get_availability()

        # Should have entries for multiple floors
        floors = set(a["floor"] for a in availability)
        assert len(floors) >= 4  # Floors 1-4

    def test_get_availability_filtered_by_type(self):
        """Test availability filtered by space type."""
        ev_availability = self.store.get_availability(space_type="ev")

        assert len(ev_availability) > 0
        assert all(a["space_type"] == "ev" for a in ev_availability)

    def test_get_total_availability(self):
        """Test summary availability calculation."""
        totals = self.store.get_total_availability()

        # Should have entries for different space types
        assert "standard" in totals
        assert totals["standard"]["available"] > 0
        assert totals["standard"]["total"] > totals["standard"]["available"]

    def test_get_dynamic_context(self):
        """Test that dynamic context string is properly formatted."""
        context = self.store.get_dynamic_context()

        # Should contain section headers
        assert "WORKING HOURS" in context
        assert "PARKING PRICES" in context
        assert "CURRENT AVAILABILITY" in context

        # Should contain actual data
        assert "Monday" in context
        assert "$3.00" in context

    def test_double_initialization_skipped(self):
        """Test that initializing twice doesn't duplicate data."""
        # Initialize again (should be skipped)
        self.store.initialize_default_data()

        # Should still have only 7 days
        hours = self.store.get_working_hours()
        assert len(hours) == 7
