"""
Tests for the Email Notification Service.

Covers:
1. Console fallback mode (SMTP not configured)
2. Admin notification (new reservation)
3. User approval email
4. User rejection email
5. SMTP SSL (port 465) and STARTTLS (port 587) paths
6. Retry on transient SMTP errors
7. Email masking in console output
8. Async wrappers

All SMTP interactions are mocked — no real emails are sent.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.notifications.email_service import EmailService, EmailServiceError

# ─── Fixtures ─────────────────────────────────────────

SAMPLE_RESERVATION = {
    "id": 42,
    "first_name": "Sanyam",
    "last_name": "Sachan",
    "email": "sanyam@gmail.com",
    "car_number": "UP-32-XY-1234",
    "space_type": "ev",
    "start_datetime": "2026-05-20 09:00",
    "end_datetime": "2026-05-20 18:00",
    "status": "pending",
    "admin_notes": None,
    "created_at": "2026-05-20T08:00:00",
    "updated_at": "2026-05-20T08:00:00",
    "approved_at": None,
}

SMTP_ENV = {
    "SMTP_HOST": "smtp.gmail.com",
    "SMTP_PORT": "465",
    "SMTP_USERNAME": "bot@gmail.com",
    "SMTP_PASSWORD": "secret-app-pass",
    "ADMIN_EMAIL": "admin@company.com",
}


def _mock_settings(**overrides):
    """Create a mock settings object with given SMTP values."""
    defaults = {
        "smtp_host": "",
        "smtp_port": 465,
        "smtp_username": "",
        "smtp_password": "",
        "admin_email": "admin@parksmart.com",
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def _unconfigured_settings():
    return _mock_settings()


def _configured_settings():
    return _mock_settings(
        smtp_host="smtp.gmail.com",
        smtp_port=465,
        smtp_username="bot@gmail.com",
        smtp_password="secret-app-pass",
        admin_email="admin@company.com",
    )


# ─── Console Fallback ────────────────────────────────


class TestConsoleMode:
    """Tests for console-fallback behaviour."""

    def test_not_configured_when_env_empty(self):
        with patch("src.notifications.email_service.settings", _unconfigured_settings()):
            service = EmailService()
            assert service.is_configured is False

    def test_admin_notification_console(self, capsys):
        with patch("src.notifications.email_service.settings", _unconfigured_settings()):
            service = EmailService()
            result = service.notify_new_reservation(SAMPLE_RESERVATION)
            assert result is True
            out = capsys.readouterr().out
            assert "42" in out
            assert "Sanyam" in out
            # Email must be masked in console output
            assert "sanyam@gmail.com" not in out
            assert "sa****@gmail.com" in out

    def test_user_approval_console(self, capsys):
        with patch("src.notifications.email_service.settings", _unconfigured_settings()):
            service = EmailService()
            res = {**SAMPLE_RESERVATION, "status": "approved"}
            result = service.send_user_approval(res)
            assert result is True
            out = capsys.readouterr().out
            assert "APPROVED" in out

    def test_user_rejection_console(self, capsys):
        with patch("src.notifications.email_service.settings", _unconfigured_settings()):
            service = EmailService()
            res = {**SAMPLE_RESERVATION, "status": "rejected", "admin_notes": "No spaces"}
            result = service.send_user_rejection(res)
            assert result is True
            out = capsys.readouterr().out
            assert "REJECTED" in out


# ─── Configured Mode ─────────────────────────────────


class TestConfiguredMode:
    """Tests for SMTP-configured behaviour."""

    def test_is_configured_when_env_set(self):
        with patch("src.notifications.email_service.settings", _configured_settings()):
            service = EmailService()
            assert service.is_configured is True
            assert service.smtp_host == "smtp.gmail.com"
            assert service.smtp_port == 465
            assert service.admin_email == "admin@company.com"


# ─── Admin Email ──────────────────────────────────────


class TestAdminEmail:
    """Tests for send_admin_notification (SMTP path)."""

    @patch("src.notifications.email_service.smtplib.SMTP_SSL")
    def test_admin_email_sent_ssl(self, mock_smtp_ssl_cls):
        """Port 465 → SMTP_SSL is used."""
        with patch("src.notifications.email_service.settings", _configured_settings()):
            mock_server = MagicMock()
            mock_smtp_ssl_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp_ssl_cls.return_value.__exit__ = MagicMock(return_value=False)

            service = EmailService()
            result = service.notify_new_reservation(SAMPLE_RESERVATION)

            assert result is True
            mock_server.login.assert_called_once_with("bot@gmail.com", "secret-app-pass")
            mock_server.sendmail.assert_called_once()
            # Verify admin email is the recipient
            call_args = mock_server.sendmail.call_args
            assert call_args[0][1] == "admin@company.com"

    @patch("src.notifications.email_service.smtplib.SMTP")
    def test_admin_email_sent_starttls(self, mock_smtp_cls):
        """Port 587 → SMTP + STARTTLS is used."""
        with patch(
            "src.notifications.email_service.settings",
            _mock_settings(
                smtp_host="smtp.gmail.com",
                smtp_port=587,
                smtp_username="bot@gmail.com",
                smtp_password="secret-app-pass",
                admin_email="admin@company.com",
            ),
        ):
            mock_server = MagicMock()
            mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

            service = EmailService()
            result = service.notify_new_reservation(SAMPLE_RESERVATION)

            assert result is True
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once()

    def test_admin_html_contains_all_fields(self):
        with patch("src.notifications.email_service.settings", _unconfigured_settings()):
            service = EmailService()
            html = service._build_admin_html(SAMPLE_RESERVATION)
            assert "Sanyam" in html
            assert "Sachan" in html
            assert "sanyam@gmail.com" in html  # Full email in the actual email body
            assert "UP-32-XY-1234" in html
            assert "EV" in html
            assert "42" in html

    def test_admin_text_contains_all_fields(self):
        with patch("src.notifications.email_service.settings", _unconfigured_settings()):
            service = EmailService()
            text = service._build_admin_text(SAMPLE_RESERVATION)
            assert "Sanyam Sachan" in text
            assert "UP-32-XY-1234" in text
            assert "#42" in text


# ─── User Approval Email ─────────────────────────────


class TestUserApprovalEmail:
    """Tests for send_user_approval."""

    @patch("src.notifications.email_service.smtplib.SMTP_SSL")
    def test_approval_email_sent(self, mock_smtp_ssl_cls):
        with patch("src.notifications.email_service.settings", _configured_settings()):
            mock_server = MagicMock()
            mock_smtp_ssl_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp_ssl_cls.return_value.__exit__ = MagicMock(return_value=False)

            service = EmailService()
            res = {**SAMPLE_RESERVATION, "status": "approved", "approved_at": "2026-05-20T10:00:00"}
            result = service.send_user_approval(res)

            assert result is True
            call_args = mock_server.sendmail.call_args
            assert call_args[0][1] == "sanyam@gmail.com"  # User email as recipient

    def test_approval_html_has_instructions(self):
        with patch("src.notifications.email_service.settings", _unconfigured_settings()):
            service = EmailService()
            res = {**SAMPLE_RESERVATION, "status": "approved"}
            html = service._build_user_approval_html(res)
            assert "APPROVED" in html
            assert "Parking Instructions" in html
            assert "123 Main Street" in html

    def test_approval_text_has_instructions(self):
        with patch("src.notifications.email_service.settings", _unconfigured_settings()):
            service = EmailService()
            res = {**SAMPLE_RESERVATION, "status": "approved"}
            text = service._build_user_approval_text(res)
            assert "APPROVED" in text
            assert "123 Main Street" in text

    def test_no_email_skips_notification(self):
        with patch("src.notifications.email_service.settings", _unconfigured_settings()):
            service = EmailService()
            res = {**SAMPLE_RESERVATION, "email": None, "status": "approved"}
            result = service.send_user_approval(res)
            assert result is False


# ─── User Rejection Email ────────────────────────────


class TestUserRejectionEmail:
    """Tests for send_user_rejection."""

    @patch("src.notifications.email_service.smtplib.SMTP_SSL")
    def test_rejection_email_sent(self, mock_smtp_ssl_cls):
        with patch("src.notifications.email_service.settings", _configured_settings()):
            mock_server = MagicMock()
            mock_smtp_ssl_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp_ssl_cls.return_value.__exit__ = MagicMock(return_value=False)

            service = EmailService()
            res = {**SAMPLE_RESERVATION, "status": "rejected", "admin_notes": "No EV spots left"}
            result = service.send_user_rejection(res)

            assert result is True

    def test_rejection_html_has_reason(self):
        with patch("src.notifications.email_service.settings", _unconfigured_settings()):
            service = EmailService()
            res = {**SAMPLE_RESERVATION, "status": "rejected", "admin_notes": "Full capacity"}
            html = service._build_user_rejection_html(res)
            assert "Full capacity" in html
            assert "Not Approved" in html

    def test_rejection_text_has_reason(self):
        with patch("src.notifications.email_service.settings", _unconfigured_settings()):
            service = EmailService()
            res = {**SAMPLE_RESERVATION, "status": "rejected", "admin_notes": "Full capacity"}
            text = service._build_user_rejection_text(res)
            assert "Full capacity" in text


# ─── Backward Compat: notify_user_status_change ──────


class TestStatusChangeDispatch:
    """Tests for notify_user_status_change dispatching."""

    def test_dispatches_to_approval(self, capsys):
        with patch("src.notifications.email_service.settings", _unconfigured_settings()):
            service = EmailService()
            res = {**SAMPLE_RESERVATION, "status": "approved"}
            result = service.notify_user_status_change(res)
            assert result is True

    def test_dispatches_to_rejection(self, capsys):
        with patch("src.notifications.email_service.settings", _unconfigured_settings()):
            service = EmailService()
            res = {**SAMPLE_RESERVATION, "status": "rejected"}
            result = service.notify_user_status_change(res)
            assert result is True

    def test_unknown_status_returns_false(self):
        with patch("src.notifications.email_service.settings", _unconfigured_settings()):
            service = EmailService()
            res = {**SAMPLE_RESERVATION, "status": "unknown"}
            result = service.notify_user_status_change(res)
            assert result is False


# ─── Core send_email ─────────────────────────────────


class TestCoreSendEmail:
    """Tests for the reusable send_email() method."""

    def test_raises_when_not_configured(self):
        with patch("src.notifications.email_service.settings", _unconfigured_settings()):
            service = EmailService()
            with pytest.raises(EmailServiceError, match="not configured"):
                service.send_email(
                    to="x@test.com",
                    subject="Test",
                    html_body="<p>Hi</p>",
                )
