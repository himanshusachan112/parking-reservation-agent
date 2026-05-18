"""
Tests for the Email Notification Service.

Tests cover:
1. Console fallback mode (when SMTP is not configured)
2. Notification formatting
3. Email HTML generation
4. SMTP send (mocked)

We test the email service without actually sending emails
by mocking the SMTP connection.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.notifications.email_service import EmailService


class TestEmailService:
    """Tests for the EmailService class."""

    def test_console_mode_when_smtp_not_configured(self):
        """When SMTP vars are not set, service should be in console mode."""
        # Clear all SMTP env vars to ensure console fallback
        with patch.dict("os.environ", {}, clear=True):
            service = EmailService()
            assert service.is_configured is False

    def test_configured_mode_when_smtp_set(self):
        """When SMTP vars are set, service should be in configured mode."""
        env = {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_PORT": "587",
            "SMTP_USERNAME": "test@test.com",
            "SMTP_PASSWORD": "secret",
            "ADMIN_EMAIL": "admin@test.com",
        }
        with patch.dict("os.environ", env, clear=True):
            service = EmailService()
            assert service.is_configured is True
            assert service.smtp_host == "smtp.test.com"
            assert service.admin_email == "admin@test.com"

    def test_console_notification(self, capsys):
        """Console fallback should print reservation details."""
        with patch.dict("os.environ", {}, clear=True):
            service = EmailService()
            reservation = {
                "id": 42,
                "first_name": "Test",
                "last_name": "User",
                "car_number": "ABC-999",
                "space_type": "ev",
                "start_datetime": "2026-05-20 09:00",
                "end_datetime": "2026-05-20 18:00",
                "status": "pending",
            }
            result = service.notify_new_reservation(reservation)
            assert result is True

            captured = capsys.readouterr()
            assert "42" in captured.out
            assert "Test" in captured.out
            assert "ABC-999" in captured.out

    def test_email_text_body(self):
        """Plain text email body should contain reservation details."""
        with patch.dict("os.environ", {}, clear=True):
            service = EmailService()
            reservation = {
                "id": 7,
                "first_name": "Jane",
                "last_name": "Doe",
                "car_number": "JD-555",
                "space_type": "vip",
                "start_datetime": "2026-06-01 10:00",
                "end_datetime": "2026-06-01 20:00",
            }
            text = service._build_email_text(reservation)
            assert "Jane Doe" in text
            assert "JD-555" in text
            assert "vip" in text
            assert "#7" in text

    def test_email_html_body(self):
        """HTML email body should contain reservation details with markup."""
        with patch.dict("os.environ", {}, clear=True):
            service = EmailService()
            reservation = {
                "id": 3,
                "first_name": "Mark",
                "last_name": "Lee",
                "car_number": "ML-100",
                "space_type": "standard",
                "start_datetime": "2026-07-01 08:00",
                "end_datetime": "2026-07-01 16:00",
            }
            html = service._build_email_html(reservation)
            assert "Mark" in html
            assert "ML-100" in html
            assert "STANDARD" in html
            assert "<html>" in html

    @patch("smtplib.SMTP")
    def test_send_email_via_smtp(self, mock_smtp_class):
        """When SMTP is configured, email should be sent via SMTP."""
        env = {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_PORT": "587",
            "SMTP_USERNAME": "test@test.com",
            "SMTP_PASSWORD": "secret",
            "ADMIN_EMAIL": "admin@test.com",
        }
        with patch.dict("os.environ", env, clear=True):
            # Setup mock SMTP instance
            mock_server = MagicMock()
            mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

            service = EmailService()
            reservation = {
                "id": 1,
                "first_name": "Test",
                "last_name": "Email",
                "car_number": "TE-001",
                "space_type": "standard",
                "start_datetime": "2026-05-20 09:00",
                "end_datetime": "2026-05-20 18:00",
            }
            result = service._send_email(reservation)
            assert result is True
            # Verify SMTP methods were called
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("test@test.com", "secret")
            mock_server.sendmail.assert_called_once()
