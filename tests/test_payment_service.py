"""
Tests for PaymentService.

Covers:
  - create_payment: success, idempotency
  - get_payment: found, not-found, lazy expiry transition
  - process_payment: success, already-paid guard, expired guard, bad method
  - Email: payment confirmation text/HTML builders
"""

import pytest
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.base import Base
from src.models.payment import (
    PAYMENT_EXPIRED,
    PAYMENT_PAID,
    PAYMENT_PENDING,
    Payment,
)
from src.repositories.payment_repository import PaymentRepository
from src.services.payment_service import (
    AlreadyPaidError,
    PaymentError,
    PaymentExpiredError,
    PaymentNotFoundError,
    PaymentService,
)

# ── In-memory SQLite engine shared across the module ─────────────────────────
_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
# Create only the payments table (Payment model)
Base.metadata.create_all(_engine)
_Session = sessionmaker(bind=_engine, expire_on_commit=False)


@contextmanager
def _test_db_session():
    db = _Session()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def patch_db_session():
    """Redirect PaymentService db_session calls to the in-memory SQLite."""
    targets = [
        "src.services.payment_service.db_session",
    ]
    patches = [patch(t, _test_db_session) for t in targets]
    for p in patches:
        p.start()
    yield
    for p in patches:
        p.stop()


@pytest.fixture(autouse=True)
def clean_payments():
    """Truncate payments table before each test for isolation."""
    db = _Session()
    db.query(Payment).delete()
    db.commit()
    db.close()
    yield


@pytest.fixture
def svc():
    return PaymentService()


@pytest.fixture
def repo():
    return PaymentRepository()


def _make_payment(svc: PaymentService, reservation_id: int = 1, amount: float = 450.0) -> dict:
    return svc.create_payment(
        reservation_id=reservation_id,
        amount_inr=Decimal(str(amount)),
        user_name="Alice Johnson",
        user_email="alice@example.com",
        vehicle_number="TS09AB1234",
        space_type="standard",
        start_datetime="2026-06-01 09:00",
        end_datetime="2026-06-01 18:00",
    )


# ── create_payment ────────────────────────────────────────────────────────────


class TestCreatePayment:
    def test_creates_pending_payment(self, svc):
        result = _make_payment(svc)

        assert result["status"] == PAYMENT_PENDING
        assert result["amount_inr"] == 450.0
        assert result["user_name"] == "Alice Johnson"
        assert result["user_email"] == "alice@example.com"
        assert result["vehicle_number"] == "TS09AB1234"
        assert result["space_type"] == "standard"
        assert result["payment_token"]  # non-empty UUID hex
        assert len(result["payment_token"]) == 32
        assert result["is_payable"] is True
        assert result["is_expired"] is False

    def test_idempotent_on_duplicate_reservation(self, svc):
        first = _make_payment(svc, reservation_id=42)
        second = _make_payment(svc, reservation_id=42)

        # Returns the same record without creating a duplicate
        assert first["id"] == second["id"]
        assert first["payment_token"] == second["payment_token"]

    def test_different_reservations_get_different_tokens(self, svc):
        a = _make_payment(svc, reservation_id=10)
        b = _make_payment(svc, reservation_id=11)
        assert a["payment_token"] != b["payment_token"]

    def test_email_lowercased(self, svc):
        result = svc.create_payment(
            reservation_id=99,
            amount_inr=Decimal("200"),
            user_name="Bob Smith",
            user_email="Bob@Example.COM",
            vehicle_number="ab1234",
            space_type="vip",
            start_datetime="2026-06-01 10:00",
            end_datetime="2026-06-01 12:00",
        )
        assert result["user_email"] == "bob@example.com"

    def test_vehicle_uppercased(self, svc):
        result = svc.create_payment(
            reservation_id=100,
            amount_inr=Decimal("100"),
            user_name="Test User",
            user_email=None,
            vehicle_number="ts09ab1234",
            space_type="standard",
            start_datetime="2026-06-01 10:00",
            end_datetime="2026-06-01 14:00",
        )
        assert result["vehicle_number"] == "TS09AB1234"

    def test_expires_at_set_within_7_days(self, svc):
        result = _make_payment(svc)
        assert result["expires_at"] is not None
        expires = datetime.fromisoformat(result["expires_at"])
        # SQLite may return tz-naive; normalise both sides to UTC
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        # Should expire ~7 days from now (allow ±5 minutes for test timing)
        delta = expires - now
        assert timedelta(days=6, hours=23) < delta <= timedelta(days=7, minutes=5)


# ── get_payment ───────────────────────────────────────────────────────────────


class TestGetPayment:
    def test_returns_none_for_unknown_token(self, svc):
        result = svc.get_payment("nonexistenttoken" * 2)
        assert result is None

    def test_returns_dict_for_valid_token(self, svc):
        created = _make_payment(svc)
        fetched = svc.get_payment(created["payment_token"])
        assert fetched is not None
        assert fetched["id"] == created["id"]
        assert fetched["status"] == PAYMENT_PENDING

    def test_lazily_expires_overdue_payment(self, svc, repo):
        """A pending payment whose expires_at has passed becomes 'expired' on get."""
        created = _make_payment(svc)
        token = created["payment_token"]

        # Back-date expires_at to the past
        db = _Session()
        p = db.query(Payment).filter_by(payment_token=token).first()
        p.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()
        db.close()

        fetched = svc.get_payment(token)
        assert fetched["status"] == PAYMENT_EXPIRED
        assert fetched["is_expired"] is True
        assert fetched["is_payable"] is False


# ── process_payment ───────────────────────────────────────────────────────────


class TestProcessPayment:
    def test_successful_upi_payment(self, svc):
        created = _make_payment(svc)
        result = svc.process_payment(
            token=created["payment_token"],
            payment_method="upi",
            upi_id="alice@upi",
        )
        assert result["status"] == PAYMENT_PAID
        assert result["payment_method"] == "upi"
        assert result["transaction_id"] is not None
        assert result["transaction_id"].startswith("TXN-")
        assert result["paid_at"] is not None
        assert result["is_payable"] is False

    def test_successful_card_payment(self, svc):
        created = _make_payment(svc, reservation_id=20)
        result = svc.process_payment(
            token=created["payment_token"],
            payment_method="card",
            card_last4="4242",
        )
        assert result["status"] == PAYMENT_PAID

    def test_successful_netbanking_payment(self, svc):
        created = _make_payment(svc, reservation_id=21)
        result = svc.process_payment(
            token=created["payment_token"],
            payment_method="netbanking",
        )
        assert result["status"] == PAYMENT_PAID

    def test_successful_wallet_payment(self, svc):
        created = _make_payment(svc, reservation_id=22)
        result = svc.process_payment(
            token=created["payment_token"],
            payment_method="wallet",
            wallet_provider="paytm",
        )
        assert result["status"] == PAYMENT_PAID

    def test_transaction_id_unique_across_payments(self, svc):
        a = _make_payment(svc, reservation_id=30)
        b = _make_payment(svc, reservation_id=31)
        r_a = svc.process_payment(a["payment_token"], "upi")
        r_b = svc.process_payment(b["payment_token"], "upi")
        assert r_a["transaction_id"] != r_b["transaction_id"]

    def test_raises_not_found_for_unknown_token(self, svc):
        with pytest.raises(PaymentNotFoundError):
            svc.process_payment("a" * 32, "upi")

    def test_raises_already_paid_on_duplicate(self, svc):
        created = _make_payment(svc, reservation_id=40)
        svc.process_payment(created["payment_token"], "upi")
        # Second attempt raises AlreadyPaidError
        with pytest.raises(AlreadyPaidError, match="already been paid"):
            svc.process_payment(created["payment_token"], "upi")

    def test_raises_expired_error_for_old_link(self, svc):
        created = _make_payment(svc, reservation_id=50)
        token = created["payment_token"]

        # Back-date expiry
        db = _Session()
        p = db.query(Payment).filter_by(payment_token=token).first()
        p.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
        db.close()

        with pytest.raises(PaymentExpiredError, match="expired"):
            svc.process_payment(token, "upi")

    def test_raises_payment_error_for_invalid_method(self, svc):
        created = _make_payment(svc, reservation_id=60)
        with pytest.raises(PaymentError, match="Invalid payment method"):
            svc.process_payment(created["payment_token"], "crypto")

    def test_paid_payment_is_no_longer_payable(self, svc):
        created = _make_payment(svc, reservation_id=70)
        svc.process_payment(created["payment_token"], "card")
        fetched = svc.get_payment(created["payment_token"])
        assert fetched["is_payable"] is False
        assert fetched["status"] == PAYMENT_PAID


# ── PaymentRepository helpers ─────────────────────────────────────────────────


class TestPaymentRepository:
    def test_to_dict_returns_expected_keys(self, svc, repo):
        created = _make_payment(svc, reservation_id=80)
        db = _Session()
        payment = db.query(Payment).filter_by(id=created["id"]).first()
        d = repo.to_dict(payment)
        db.close()

        expected_keys = {
            "id", "reservation_id", "payment_token", "status",
            "amount_inr", "payment_method", "transaction_id", "paid_at",
            "expires_at", "user_name", "user_email", "vehicle_number",
            "space_type", "start_datetime", "end_datetime",
            "is_expired", "is_payable", "created_at",
        }
        assert expected_keys.issubset(set(d.keys()))

    def test_get_by_reservation_id(self, svc, repo):
        created = _make_payment(svc, reservation_id=90)
        db = _Session()
        p = repo.get_by_reservation_id(db, 90)
        db.close()
        assert p is not None
        assert p.id == created["id"]

    def test_get_by_token(self, svc, repo):
        created = _make_payment(svc, reservation_id=91)
        db = _Session()
        p = repo.get_by_token(db, created["payment_token"])
        db.close()
        assert p is not None
        assert p.reservation_id == 91

    def test_get_by_token_returns_none_for_unknown(self, repo):
        db = _Session()
        p = repo.get_by_token(db, "z" * 32)
        db.close()
        assert p is None


# ── Email service: payment builders ──────────────────────────────────────────


class TestPaymentEmailBuilders:
    """Verify that the email builders include key content."""

    @pytest.fixture
    def email_svc(self):
        from src.notifications.email_service import EmailService
        return EmailService(
            smtp_host="",
            smtp_port=465,
            smtp_username="",
            smtp_password="",
            admin_email="admin@test.com",
        )

    @pytest.fixture
    def payment_dict(self):
        return {
            "id": 1,
            "reservation_id": 55,
            "payment_token": "a" * 32,
            "status": "paid",
            "amount_inr": 900.0,
            "payment_method": "upi",
            "transaction_id": "TXN-ABCDEF123456",
            "paid_at": "2026-06-01T12:00:00+00:00",
            "user_name": "Test User",
            "user_email": "user@test.com",
            "vehicle_number": "TS09AB1234",
            "space_type": "standard",
            "start_datetime": "2026-06-01 09:00",
            "end_datetime": "2026-06-01 18:00",
        }

    def test_text_contains_amount(self, email_svc, payment_dict):
        text = email_svc._build_payment_confirmation_text(payment_dict)
        assert "900" in text

    def test_text_contains_transaction_id(self, email_svc, payment_dict):
        text = email_svc._build_payment_confirmation_text(payment_dict)
        assert "TXN-ABCDEF123456" in text

    def test_text_contains_customer_name(self, email_svc, payment_dict):
        text = email_svc._build_payment_confirmation_text(payment_dict)
        assert "Test User" in text

    def test_html_contains_amount(self, email_svc, payment_dict):
        html = email_svc._build_payment_confirmation_html(payment_dict)
        assert "900" in html

    def test_html_contains_transaction_id(self, email_svc, payment_dict):
        html = email_svc._build_payment_confirmation_html(payment_dict)
        assert "TXN-ABCDEF123456" in html

    def test_html_contains_paid_status(self, email_svc, payment_dict):
        html = email_svc._build_payment_confirmation_html(payment_dict)
        assert "PAID" in html

    def test_console_fallback_logs_to_stdout(self, email_svc, payment_dict, capsys):
        email_svc._log_payment_to_console(payment_dict)
        captured = capsys.readouterr()
        assert "PAYMENT CONFIRMATION" in captured.out
        assert "TXN-ABCDEF123456" in captured.out

    def test_approval_text_includes_payment_link(self, email_svc):
        reservation = {
            "id": 1,
            "first_name": "Alice",
            "last_name": "Johnson",
            "email": "alice@example.com",
            "car_number": "TS09AB1234",
            "space_type": "standard",
            "start_datetime": "2026-06-01 09:00",
            "end_datetime": "2026-06-01 18:00",
        }
        text = email_svc._build_user_approval_text(
            reservation, payment_link="http://localhost:3000/payment/abc123"
        )
        assert "http://localhost:3000/payment/abc123" in text

    def test_approval_html_includes_pay_button(self, email_svc):
        reservation = {
            "id": 1,
            "first_name": "Alice",
            "last_name": "Johnson",
            "car_number": "TS09AB1234",
            "space_type": "standard",
            "start_datetime": "2026-06-01 09:00",
            "end_datetime": "2026-06-01 18:00",
        }
        html = email_svc._build_user_approval_html(
            reservation, payment_link="http://localhost:3000/payment/abc123"
        )
        assert "Pay Now" in html
        assert "http://localhost:3000/payment/abc123" in html

    def test_approval_html_without_payment_link_has_no_button(self, email_svc):
        reservation = {
            "id": 1,
            "first_name": "Alice",
            "last_name": "Johnson",
            "car_number": "TS09AB1234",
            "space_type": "standard",
            "start_datetime": "2026-06-01 09:00",
            "end_datetime": "2026-06-01 18:00",
        }
        html = email_svc._build_user_approval_html(reservation)
        assert "Pay Now" not in html


# ── API-level integration via TestClient ────────────────────────────────────


class TestPaymentAPI:
    """Integration tests for payment endpoints using FastAPI TestClient."""

    def setup_method(self):
        from unittest.mock import MagicMock
        from fastapi.testclient import TestClient
        from src.database.sql_store import SQLStore
        import src.api.server as srv

        # Inject in-memory SQL store
        self.test_store = SQLStore(database_url="sqlite:///:memory:")
        self.test_store.initialize_default_data()
        srv.sql_store = self.test_store

        # Mock email service
        srv.email_service = MagicMock()
        srv.email_service.notify_new_reservation.return_value = True

        # Inject payment service backed by same in-memory DB
        srv._payment_svc = PaymentService()

        self.client = TestClient(srv.app)
        self.srv = srv

    def _create_approved_reservation(self):
        """Insert a reservation directly and create its payment record."""
        from src.database.sql_store import SQLStore

        reservation_id = self.test_store.save_reservation({
            "first_name": "Pay",
            "last_name": "Test",
            "email": "pay@test.com",
            "car_number": "PAY-0001",
            "space_type": "standard",
            "start_datetime": "2026-06-01 09:00",
            "end_datetime": "2026-06-01 18:00",
        })
        self.test_store.update_reservation_status(reservation_id, "approved")
        payment = self.srv._payment_svc.create_payment(
            reservation_id=reservation_id,
            amount_inr=Decimal("450"),
            user_name="Pay Test",
            user_email="pay@test.com",
            vehicle_number="PAY-0001",
            space_type="standard",
            start_datetime="2026-06-01 09:00",
            end_datetime="2026-06-01 18:00",
        )
        return payment

    def test_get_payment_not_found(self):
        res = self.client.get("/api/payment/nonexistenttoken123456789012345")
        assert res.status_code == 404

    def test_get_payment_found(self):
        payment = self._create_approved_reservation()
        res = self.client.get(f"/api/payment/{payment['payment_token']}")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "pending"
        assert data["amount_inr"] == 450.0
        assert data["is_payable"] is True

    def test_process_payment_upi(self):
        payment = self._create_approved_reservation()
        token = payment["payment_token"]
        res = self.client.post(
            f"/api/payment/{token}/process",
            json={"payment_method": "upi", "upi_id": "pay@test"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "paid"
        assert data["transaction_id"].startswith("TXN-")

    def test_process_payment_already_paid_returns_409(self):
        payment = self._create_approved_reservation()
        token = payment["payment_token"]
        # First payment
        self.client.post(
            f"/api/payment/{token}/process",
            json={"payment_method": "upi"},
        )
        # Second attempt
        res = self.client.post(
            f"/api/payment/{token}/process",
            json={"payment_method": "upi"},
        )
        assert res.status_code == 409

    def test_process_payment_invalid_method_returns_400(self):
        payment = self._create_approved_reservation()
        res = self.client.post(
            f"/api/payment/{payment['payment_token']}/process",
            json={"payment_method": "bitcoin"},
        )
        assert res.status_code == 400

    def test_payment_status_endpoint(self):
        payment = self._create_approved_reservation()
        token = payment["payment_token"]
        res = self.client.get(f"/api/payment/{token}/status")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "pending"
        assert data["is_payable"] is True

    def test_payment_status_after_payment(self):
        payment = self._create_approved_reservation()
        token = payment["payment_token"]
        self.client.post(
            f"/api/payment/{token}/process",
            json={"payment_method": "card"},
        )
        res = self.client.get(f"/api/payment/{token}/status")
        data = res.json()
        assert data["status"] == "paid"
        assert data["is_payable"] is False

    def test_process_payment_updates_reservation_to_paid(self):
        """After payment, the legacy reservation should be marked 'paid'."""
        payment = self._create_approved_reservation()
        token = payment["payment_token"]
        self.client.post(
            f"/api/payment/{token}/process",
            json={"payment_method": "wallet"},
        )
        res = self.test_store.get_reservation_by_id(payment["reservation_id"])
        assert res["status"] == "paid"
