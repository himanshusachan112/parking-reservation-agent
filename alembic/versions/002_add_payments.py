"""Add payments table.

Revision ID: 002
Revises: 001
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        # Reference to legacy reservations table (no FK — keeps schema portable)
        sa.Column("reservation_id", sa.Integer(), nullable=False),
        # Secure URL token embedded in the payment link
        sa.Column("payment_token", sa.String(64), nullable=False, unique=True),
        # Status: pending / paid / failed / expired
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        # Amount locked at approval time
        sa.Column("amount_inr", sa.Numeric(10, 2), nullable=False),
        # Populated after successful payment
        sa.Column("payment_method", sa.String(50), nullable=True),
        sa.Column("transaction_id", sa.String(100), nullable=True, unique=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        # Payment window expiry
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        # Denormalised booking snapshot for email / payment page
        sa.Column("user_name", sa.String(200), nullable=True),
        sa.Column("user_email", sa.String(200), nullable=True),
        sa.Column("vehicle_number", sa.String(50), nullable=True),
        sa.Column("space_type", sa.String(50), nullable=True),
        sa.Column("start_datetime", sa.String(100), nullable=True),
        sa.Column("end_datetime", sa.String(100), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_payments_reservation_id", "payments", ["reservation_id"])
    op.create_index("ix_payments_payment_token", "payments", ["payment_token"])
    op.create_index("ix_payments_status", "payments", ["status"])


def downgrade() -> None:
    op.drop_index("ix_payments_status", table_name="payments")
    op.drop_index("ix_payments_payment_token", table_name="payments")
    op.drop_index("ix_payments_reservation_id", table_name="payments")
    op.drop_table("payments")
