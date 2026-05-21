"""Initial schema – all tables for ParkSmart PostgreSQL.

Creates:
  Legacy (sql_store.py):  working_hours, parking_prices,
                          parking_availability, reservations
  Production (new):       parking_types, parking_slots,
                          bookings, admin_actions

Revision ID: 001
Revises: (none – first migration)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # Legacy tables (mirrors sql_store.py ORM models)                     #
    # ------------------------------------------------------------------ #
    op.create_table(
        "working_hours",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("day_of_week", sa.String(), nullable=False, unique=True),
        sa.Column("open_time", sa.String(), nullable=False),
        sa.Column("close_time", sa.String(), nullable=False),
        sa.Column("is_open", sa.Boolean(), nullable=True, server_default=sa.true()),
    )

    op.create_table(
        "parking_prices",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("space_type", sa.String(), nullable=False),
        sa.Column("duration_type", sa.String(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(), nullable=True, server_default="INR"),
    )

    op.create_table(
        "parking_availability",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("floor", sa.Integer(), nullable=False),
        sa.Column("space_type", sa.String(), nullable=False),
        sa.Column("total_spaces", sa.Integer(), nullable=False),
        sa.Column("available_spaces", sa.Integer(), nullable=False),
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "reservations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("car_number", sa.String(), nullable=False),
        sa.Column("space_type", sa.String(), nullable=False),
        sa.Column("start_datetime", sa.String(), nullable=False),
        sa.Column("end_datetime", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=True, server_default="pending"),
        sa.Column("admin_notes", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ------------------------------------------------------------------ #
    # Production tables                                                    #
    # ------------------------------------------------------------------ #
    op.create_table(
        "parking_types",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(50), nullable=False, unique=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("total_slots", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_slots", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hourly_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("daily_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("monthly_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("features", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "parking_slots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("slot_number", sa.String(20), nullable=False, unique=True),
        sa.Column(
            "parking_type_id",
            sa.Integer(),
            sa.ForeignKey("parking_types.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("floor_number", sa.String(10), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="available"),
        # current_booking_id added after bookings table is created (see below)
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("booking_reference", sa.String(20), nullable=False, unique=True),
        sa.Column("user_name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("vehicle_number", sa.String(50), nullable=False),
        sa.Column("vehicle_type", sa.String(50), nullable=True),
        sa.Column(
            "parking_type_id",
            sa.Integer(),
            sa.ForeignKey("parking_types.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "assigned_slot_id",
            sa.Integer(),
            sa.ForeignKey("parking_slots.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("booking_duration_hours", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("legacy_reservation_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Add current_booking_id FK to parking_slots now that bookings table exists
    op.add_column(
        "parking_slots",
        sa.Column(
            "current_booking_id",
            sa.Integer(),
            sa.ForeignKey("bookings.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.create_table(
        "admin_actions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "booking_id",
            sa.Integer(),
            sa.ForeignKey("bookings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("admin_email", sa.String(200), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ------------------------------------------------------------------ #
    # Indexes                                                              #
    # ------------------------------------------------------------------ #
    op.create_index("ix_bookings_status", "bookings", ["status"])
    op.create_index("ix_bookings_email", "bookings", ["email"])
    op.create_index("ix_bookings_vehicle_number", "bookings", ["vehicle_number"])
    op.create_index("ix_parking_slots_parking_type_id", "parking_slots", ["parking_type_id"])
    op.create_index("ix_parking_slots_status", "parking_slots", ["status"])
    op.create_index("ix_reservations_status", "reservations", ["status"])


def downgrade() -> None:
    op.drop_table("admin_actions")
    op.drop_table("bookings")
    op.drop_table("parking_slots")
    op.drop_table("parking_types")
    op.drop_table("reservations")
    op.drop_table("parking_availability")
    op.drop_table("parking_prices")
    op.drop_table("working_hours")
