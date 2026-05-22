"""
Payment model – tracks payment lifecycle for each approved reservation.

A Payment record is created when admin approves a reservation.
The unique `payment_token` (UUID hex) is embedded in the payment URL sent
to the user.  The user completes payment on the frontend; the backend then
transitions status pending → paid and notifies the admin.

Status transitions:
  pending  →  paid      (successful payment)
  pending  →  failed    (gateway failure / user aborted)
  pending  →  expired   (expires_at passed)
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, Numeric, String

from src.database.base import Base, TimestampMixin

# ── Status constants ──────────────────────────────────────────────────────────
PAYMENT_PENDING = "pending"
PAYMENT_PAID = "paid"
PAYMENT_FAILED = "failed"
PAYMENT_EXPIRED = "expired"

VALID_PAYMENT_STATUSES = {
    PAYMENT_PENDING,
    PAYMENT_PAID,
    PAYMENT_FAILED,
    PAYMENT_EXPIRED,
}

# Supported payment methods (mock gateway)
VALID_PAYMENT_METHODS = {"upi", "card", "netbanking", "wallet"}


def _generate_payment_token() -> str:
    """Return a cryptographically-secure 32-character hex token."""
    return uuid.uuid4().hex


class Payment(Base, TimestampMixin):
    """One-to-one record tracking payment for an approved reservation."""

    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Legacy reservations.id — not a FK to keep the payment table
    # deployable independently of the legacy SQLite schema.
    reservation_id = Column(Integer, nullable=False, index=True)

    # URL token — embedded in the payment link, e.g.
    #   http://localhost:3000/payment/<payment_token>
    payment_token = Column(
        String(64),
        nullable=False,
        unique=True,
        default=_generate_payment_token,
    )

    # Lifecycle status
    status = Column(String(20), default=PAYMENT_PENDING, nullable=False)

    # Amount locked at approval time (INR)
    amount_inr = Column(Numeric(10, 2), nullable=False)

    # Populated after successful payment
    payment_method = Column(String(50), nullable=True)  # upi/card/netbanking/wallet
    transaction_id = Column(String(100), nullable=True, unique=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)

    # Link expires after this timestamp (default: 7 days from creation)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Denormalised booking snapshot so the payment page and emails work
    # without extra joins to the legacy reservations table.
    user_name = Column(String(200), nullable=True)
    user_email = Column(String(200), nullable=True)
    vehicle_number = Column(String(50), nullable=True)
    space_type = Column(String(50), nullable=True)
    start_datetime = Column(String(100), nullable=True)
    end_datetime = Column(String(100), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<Payment token={self.payment_token[:8]}... "
            f"reservation=#{self.reservation_id} status={self.status!r}>"
        )

    @property
    def is_expired(self) -> bool:
        """True if the payment window has closed."""
        if self.expires_at is None:
            return False
        expires = self.expires_at
        # SQLite returns timezone-naive datetimes; make comparison safe.
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expires

    @property
    def is_payable(self) -> bool:
        """True when the user can still make a payment."""
        return self.status == PAYMENT_PENDING and not self.is_expired
