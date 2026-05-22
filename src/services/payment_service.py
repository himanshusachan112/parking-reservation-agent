"""
PaymentService – manages payment creation, processing, and idempotency.

Design principles
-----------------
* Idempotent creation: calling create_payment() twice for the same
  reservation_id returns the existing record instead of creating a duplicate.
* No double-payment: process_payment() raises AlreadyPaidError when the
  payment record is already in "paid" state.
* Expiry guard: process_payment() raises PaymentExpiredError and transitions
  the status to "expired" when the payment window has closed.
* Mock gateway: simulates immediate success; in production swap
  _call_gateway() for a real Razorpay / PayU / Stripe call.
"""

import logging
import secrets
import string
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Optional

from src.database.session import db_session
from src.models.payment import (
    PAYMENT_EXPIRED,
    PAYMENT_PAID,
    PAYMENT_PENDING,
)
from src.repositories.payment_repository import PaymentRepository

logger = logging.getLogger(__name__)

_payment_repo = PaymentRepository()


# ── Custom exceptions ─────────────────────────────────────────────────────────


class PaymentError(RuntimeError):
    """Raised for generic payment business-logic failures."""


class AlreadyPaidError(PaymentError):
    """Raised when trying to pay an already-completed reservation."""


class PaymentExpiredError(PaymentError):
    """Raised when the payment link has passed its expiry date."""


class PaymentNotFoundError(PaymentError):
    """Raised when no payment record matches the supplied token."""


# ── Helpers ───────────────────────────────────────────────────────────────────


def _generate_transaction_id() -> str:
    """Return a transaction ID like TXN-A1B2C3D4E5F6."""
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(secrets.choice(chars) for _ in range(12))
    return f"TXN-{suffix}"


# ── Service ───────────────────────────────────────────────────────────────────


class PaymentService:
    """High-level payment lifecycle operations."""

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_payment(
        self,
        reservation_id: int,
        amount_inr: Decimal,
        user_name: str,
        user_email: Optional[str],
        vehicle_number: str,
        space_type: str,
        start_datetime: str,
        end_datetime: str,
        expires_days: int = 7,
    ) -> Dict:
        """
        Create a pending payment record for an approved reservation.

        Idempotent: if a record already exists for *reservation_id*, the
        existing record is returned unchanged.

        Returns the serialised Payment dict (including payment_token).
        """
        with db_session() as db:
            existing = _payment_repo.get_by_reservation_id(db, reservation_id)
            if existing:
                logger.info(
                    "[payment] Already exists for reservation #%d — returning existing token",
                    reservation_id,
                )
                return _payment_repo.to_dict(existing)

            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
            payment = _payment_repo.create(
                db,
                reservation_id=reservation_id,
                amount_inr=amount_inr,
                user_name=user_name,
                user_email=user_email.lower() if user_email else None,
                vehicle_number=vehicle_number.upper() if vehicle_number else None,
                space_type=space_type,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                expires_at=expires_at,
            )
            db.commit()
            db.refresh(payment)
            result = _payment_repo.to_dict(payment)

        logger.info(
            "[payment] Created token=%s... reservation=#%d amount=₹%.2f",
            result["payment_token"][:8],
            reservation_id,
            result["amount_inr"],
        )
        return result

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_payment(self, token: str) -> Optional[Dict]:
        """
        Retrieve payment details by URL token.

        Automatically transitions pending→expired when the window has closed.
        Returns None if no payment exists for that token.
        """
        with db_session() as db:
            payment = _payment_repo.get_by_token(db, token)
            if payment is None:
                return None
            # Lazily expire if window has closed
            if payment.status == PAYMENT_PENDING and payment.is_expired:
                _payment_repo.mark_expired(db, payment)
                db.commit()
                db.refresh(payment)
            return _payment_repo.to_dict(payment)

    def get_payment_by_reservation(self, reservation_id: int) -> Optional[Dict]:
        """Return the payment dict for a given reservation, or None."""
        with db_session() as db:
            payment = _payment_repo.get_by_reservation_id(db, reservation_id)
            if payment is None:
                return None
            return _payment_repo.to_dict(payment)

    # ------------------------------------------------------------------
    # Process
    # ------------------------------------------------------------------

    def process_payment(
        self,
        token: str,
        payment_method: str,
        upi_id: Optional[str] = None,
        card_last4: Optional[str] = None,
        wallet_provider: Optional[str] = None,
    ) -> Dict:
        """
        Process a payment via the mock gateway.

        In production replace ``_mock_gateway_charge()`` with a real gateway
        call (Razorpay, PayU, Stripe, etc.).

        Returns the updated Payment dict on success.

        Raises:
            PaymentNotFoundError  – token not found
            AlreadyPaidError      – booking already paid
            PaymentExpiredError   – link has expired
            PaymentError          – gateway / validation failure
        """
        if payment_method not in {"upi", "card", "netbanking", "wallet"}:
            raise PaymentError(
                f"Invalid payment method '{payment_method}'. "
                "Choose: upi, card, netbanking, wallet"
            )

        with db_session() as db:
            payment = _payment_repo.get_by_token(db, token)
            if payment is None:
                raise PaymentNotFoundError("Payment link not found or already used.")

            if payment.status == PAYMENT_PAID:
                raise AlreadyPaidError(
                    "This booking has already been paid. "
                    f"Transaction ID: {payment.transaction_id}"
                )

            if payment.is_expired or payment.status == PAYMENT_EXPIRED:
                if payment.status != PAYMENT_EXPIRED:
                    _payment_repo.mark_expired(db, payment)
                    db.commit()
                raise PaymentExpiredError(
                    "Payment link has expired. Please contact support to renew."
                )

            # ── Mock gateway charge (always succeeds for demo) ─────────────
            transaction_id = _generate_transaction_id()

            _payment_repo.mark_paid(db, payment, payment_method, transaction_id)
            db.commit()
            db.refresh(payment)
            result = _payment_repo.to_dict(payment)

        logger.info(
            "[payment] PAID token=%s... txn=%s method=%s amount=₹%.2f",
            token[:8],
            transaction_id,
            payment_method,
            result["amount_inr"],
        )
        return result
