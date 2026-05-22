"""
PaymentRepository – CRUD operations for the payments table.
"""

from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.payment import PAYMENT_EXPIRED, PAYMENT_PAID, Payment


class PaymentRepository:
    """Read/write access to the payments table."""

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_by_token(self, db: Session, token: str) -> Optional[Payment]:
        return db.execute(
            select(Payment).where(Payment.payment_token == token)
        ).scalar_one_or_none()

    def get_by_reservation_id(
        self, db: Session, reservation_id: int
    ) -> Optional[Payment]:
        return db.execute(
            select(Payment).where(Payment.reservation_id == reservation_id)
        ).scalar_one_or_none()

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def create(self, db: Session, **kwargs) -> Payment:
        payment = Payment(**kwargs)
        db.add(payment)
        db.flush()
        return payment

    def mark_paid(
        self,
        db: Session,
        payment: Payment,
        payment_method: str,
        transaction_id: str,
    ) -> Payment:
        from datetime import datetime, timezone

        payment.status = PAYMENT_PAID
        payment.payment_method = payment_method
        payment.transaction_id = transaction_id
        payment.paid_at = datetime.now(timezone.utc)
        db.flush()
        return payment

    def mark_expired(self, db: Session, payment: Payment) -> Payment:
        payment.status = PAYMENT_EXPIRED
        db.flush()
        return payment

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self, payment: Payment) -> Dict:
        return {
            "id": payment.id,
            "reservation_id": payment.reservation_id,
            "payment_token": payment.payment_token,
            "status": payment.status,
            "amount_inr": float(payment.amount_inr) if payment.amount_inr is not None else 0.0,
            "payment_method": payment.payment_method,
            "transaction_id": payment.transaction_id,
            "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
            "expires_at": payment.expires_at.isoformat() if payment.expires_at else None,
            "user_name": payment.user_name,
            "user_email": payment.user_email,
            "vehicle_number": payment.vehicle_number,
            "space_type": payment.space_type,
            "start_datetime": payment.start_datetime,
            "end_datetime": payment.end_datetime,
            "is_expired": payment.is_expired,
            "is_payable": payment.is_payable,
            "created_at": payment.created_at.isoformat() if payment.created_at else None,
        }
