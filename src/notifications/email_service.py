"""
Email Notification Service — Enterprise-Grade SMTP Integration.

This module provides async-capable email notifications for:
- Admin alerts on new reservation submissions
- User approval notifications with parking instructions
- User rejection notifications with optional reason

Features:
- SMTP SSL (port 465) and STARTTLS (port 587) support
- Async sending via asyncio for non-blocking FastAPI integration
- Retry handling with exponential backoff (3 attempts)
- Structured logging (no raw credentials in output)
- Email masking in terminal/log output
- Graceful console fallback when SMTP is not configured
- Reusable send_email() core

CONFIGURATION (.env):
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=465
  SMTP_USERNAME=your-email@gmail.com
  SMTP_PASSWORD=your-app-password   (Gmail App Password)
  ADMIN_EMAIL=admin@example.com
"""

import asyncio
import logging
import smtplib
import ssl
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config.settings import settings
from src.utils.masking import mask_email

logger = logging.getLogger(__name__)


class EmailServiceError(Exception):
    """Base exception for email service failures."""


class EmailService:
    """
    Enterprise-grade email notification service.

    Sends formatted HTML emails for reservation events. Falls back
    to structured console logging when SMTP is not configured.
    """

    def __init__(
        self,
        smtp_host: str = None,
        smtp_port: int = None,
        smtp_username: str = None,
        smtp_password: str = None,
        admin_email: str = None,
    ):
        """
        Initialise from explicit args or pydantic settings (.env).

        Args:
            smtp_host:     SMTP server hostname (default: from settings).
            smtp_port:     SMTP server port (default: from settings).
            smtp_username: Login username (default: from settings).
            smtp_password: Login password (default: from settings).
            admin_email:   Admin recipient (default: from settings).
        """
        self.smtp_host = smtp_host or settings.smtp_host
        self.smtp_port = smtp_port or settings.smtp_port
        self.smtp_username = smtp_username or settings.smtp_username
        self.smtp_password = smtp_password or settings.smtp_password
        self.admin_email = admin_email or settings.admin_email
        self.from_email = self.smtp_username or "noreply@parksmart.com"

        self.is_configured = bool(self.smtp_host and self.smtp_username and self.smtp_password)

        if self.is_configured:
            logger.info(
                "Email service configured (SMTP: %s, port: %d)",
                self.smtp_host,
                self.smtp_port,
            )
            print(f"✓ Email service configured (SMTP: {self.smtp_host})")
        else:
            logger.info("Email service in console-fallback mode (SMTP not configured)")
            print("ℹ Email service in console mode (SMTP not configured)")

    # ──────────────────────────────────────────────────
    # Core reusable send
    # ──────────────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((smtplib.SMTPException, OSError)),
        reraise=True,
    )
    def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        plain_body: str = "",
    ) -> bool:
        """
        Send a single email via SMTP with retry handling.

        Supports both SSL (port 465) and STARTTLS (port 587).

        Args:
            to:         Recipient email address.
            subject:    Email subject line.
            html_body:  HTML content.
            plain_body: Plain-text fallback (optional).

        Returns:
            True on success.

        Raises:
            EmailServiceError: When SMTP is not configured.
            smtplib.SMTPException: After exhausting retries.
        """
        if not self.is_configured:
            raise EmailServiceError("SMTP is not configured — cannot send email.")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = to

        if plain_body:
            msg.attach(MIMEText(plain_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        # Use SSL wrapper for port 465, STARTTLS for 587
        if self.smtp_port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context) as server:
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.from_email, to, msg.as_string())
        else:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.from_email, to, msg.as_string())

        logger.info("Email sent → %s | subject=%s", mask_email(to), subject)
        return True

    async def send_email_async(
        self,
        to: str,
        subject: str,
        html_body: str,
        plain_body: str = "",
    ) -> bool:
        """Async wrapper around send_email for FastAPI endpoints."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.send_email, to, subject, html_body, plain_body)

    # ──────────────────────────────────────────────────
    # Admin notification (new reservation)
    # ──────────────────────────────────────────────────

    def notify_new_reservation(self, reservation: Dict[str, Any]) -> bool:
        """
        Notify the admin about a new pending reservation.

        Args:
            reservation: Dict with reservation details.

        Returns:
            True if notification was sent/logged successfully.
        """
        if not self.is_configured:
            return self._log_to_console("ADMIN", reservation)

        try:
            subject = "New Parking Reservation Request"
            html_body = self._build_admin_html(reservation)
            plain_body = self._build_admin_text(reservation)
            self.send_email(self.admin_email, subject, html_body, plain_body)
            print(
                f"✓ Admin notification sent to {mask_email(self.admin_email)} "
                f"for reservation #{reservation.get('id', '?')}"
            )
            return True
        except Exception as exc:
            logger.error("Admin email failed: %s — falling back to console.", exc)
            print(f"⚠ Email failed: {exc}. Falling back to console.")
            return self._log_to_console("ADMIN", reservation)

    async def notify_new_reservation_async(self, reservation: Dict[str, Any]) -> bool:
        """Async version of notify_new_reservation."""
        if not self.is_configured:
            return self._log_to_console("ADMIN", reservation)
        try:
            subject = "New Parking Reservation Request"
            html_body = self._build_admin_html(reservation)
            plain_body = self._build_admin_text(reservation)
            await self.send_email_async(self.admin_email, subject, html_body, plain_body)
            return True
        except Exception as exc:
            logger.error("Async admin email failed: %s", exc)
            return self._log_to_console("ADMIN", reservation)

    # ──────────────────────────────────────────────────
    # User notification (approval / rejection)
    # ──────────────────────────────────────────────────

    def send_user_approval(self, reservation: Dict[str, Any]) -> bool:
        """
        Send an approval email to the user with parking instructions.

        Args:
            reservation: Dict with reservation details (status must be 'approved').

        Returns:
            True if sent/logged successfully.
        """
        return self._send_user_notification(reservation, "approved")

    def send_user_rejection(self, reservation: Dict[str, Any]) -> bool:
        """
        Send a rejection email to the user with optional reason.

        Args:
            reservation: Dict with reservation details (status must be 'rejected').

        Returns:
            True if sent/logged successfully.
        """
        return self._send_user_notification(reservation, "rejected")

    def notify_user_status_change(self, reservation: Dict[str, Any]) -> bool:
        """
        Dispatch to approval or rejection based on reservation status.

        Kept for backward compatibility with existing callers.
        """
        status = reservation.get("status", "")
        if status == "approved":
            return self.send_user_approval(reservation)
        elif status == "rejected":
            return self.send_user_rejection(reservation)
        else:
            logger.warning("notify_user_status_change called with status=%s", status)
            return False

    def _send_user_notification(self, reservation: Dict[str, Any], status: str) -> bool:
        """Internal helper for user approval/rejection emails."""
        user_email = reservation.get("email")
        rid = reservation.get("id", "?")

        if not user_email:
            logger.info("No email for reservation #%s — skipping user notification.", rid)
            print(f"ℹ No email for reservation #{rid} — skipping user notification.")
            return False

        if not self.is_configured:
            return self._log_to_console("USER", reservation, status)

        try:
            if status == "approved":
                subject = f"ParkSmart — Reservation #{rid} Approved ✅"
                html_body = self._build_user_approval_html(reservation)
                plain_body = self._build_user_approval_text(reservation)
            else:
                subject = f"ParkSmart — Reservation #{rid} Update"
                html_body = self._build_user_rejection_html(reservation)
                plain_body = self._build_user_rejection_text(reservation)

            self.send_email(user_email, subject, html_body, plain_body)
            print(f"✓ User notification sent to {mask_email(user_email)} " f"for reservation #{rid}")
            return True
        except Exception as exc:
            logger.error("User email failed for #%s: %s", rid, exc)
            print(f"⚠ User email failed: {exc}. Falling back to console.")
            return self._log_to_console("USER", reservation, status)

    async def send_user_approval_async(self, reservation: Dict[str, Any]) -> bool:
        """Async version of send_user_approval."""
        return await asyncio.get_event_loop().run_in_executor(None, self.send_user_approval, reservation)

    async def send_user_rejection_async(self, reservation: Dict[str, Any]) -> bool:
        """Async version of send_user_rejection."""
        return await asyncio.get_event_loop().run_in_executor(None, self.send_user_rejection, reservation)

    # ──────────────────────────────────────────────────
    # Console fallback
    # ──────────────────────────────────────────────────

    def _log_to_console(
        self,
        audience: str,
        reservation: Dict[str, Any],
        status: str = None,
    ) -> bool:
        """Print a structured notification to the console."""
        rid = reservation.get("id", "?")
        name = f"{reservation.get('first_name', '')} {reservation.get('last_name', '')}".strip()
        raw_email = reservation.get("email", "N/A")
        masked = mask_email(raw_email) if raw_email and raw_email != "N/A" else "N/A"

        print("\n" + "=" * 55)
        if audience == "ADMIN":
            print("  📧 ADMIN NOTIFICATION (console mode)")
            print("=" * 55)
            print(f"  New reservation #{rid} needs review!")
            print(f"  Name:    {name}")
            print(f"  Email:   {masked}")
            print(f"  Vehicle: {reservation.get('car_number', '')}")
            print(f"  Space:   {reservation.get('space_type', '')}")
            print(f"  Period:  {reservation.get('start_datetime', '')} → {reservation.get('end_datetime', '')}")
            print(f"  Status:  {reservation.get('status', 'pending')}")
            print("=" * 55)
            print("  → Run 'python main.py --admin' to review")
        else:
            status_emoji = "✅" if status == "approved" else "🚫"
            print(f"  📧 USER NOTIFICATION (console mode)")
            print("=" * 55)
            print(f"  To:      {masked}")
            print(f"  Reservation #{rid} has been {status_emoji} {(status or '').upper()}!")
            print(f"  Name:    {name}")
            print(f"  Vehicle: {reservation.get('car_number', '')}")
            print(f"  Space:   {reservation.get('space_type', '')}")
            print(f"  Period:  {reservation.get('start_datetime', '')} → {reservation.get('end_datetime', '')}")
            if reservation.get("admin_notes"):
                print(f"  Notes:   {reservation.get('admin_notes')}")
        print("=" * 55 + "\n")
        return True

    # ──────────────────────────────────────────────────
    # Admin email builders
    # ──────────────────────────────────────────────────

    def _build_admin_text(self, reservation: Dict[str, Any]) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        return (
            f"New Parking Reservation Request\n"
            f"{'=' * 40}\n\n"
            f"Reservation ID: #{reservation.get('id', '?')}\n"
            f"Full Name: {reservation.get('first_name', '')} {reservation.get('last_name', '')}\n"
            f"Email: {reservation.get('email', 'N/A')}\n"
            f"Vehicle Number: {reservation.get('car_number', '')}\n"
            f"Vehicle Type: {reservation.get('space_type', '')}\n"
            f"Start Time: {reservation.get('start_datetime', '')}\n"
            f"End Time: {reservation.get('end_datetime', '')}\n"
            f"Submitted At: {reservation.get('created_at', now)}\n"
            f"Status: PENDING — Awaiting your review\n\n"
            f"Please review this reservation in the admin panel.\n"
        )

    def _build_admin_html(self, reservation: Dict[str, Any]) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        created = reservation.get("created_at", now)
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #1B2A4A; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">🚗 ParkSmart</h1>
                <p style="color: #64B5F6; margin: 5px 0;">New Reservation Request</p>
            </div>
            <div style="padding: 20px; background-color: #f5f5f5;">
                <h2 style="color: #1B2A4A;">Reservation #{reservation.get('id', '?')}</h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px; font-weight: bold; color: #555;">Full Name:</td>
                        <td style="padding: 8px;">{reservation.get('first_name', '')} {reservation.get('last_name', '')}</td>
                    </tr>
                    <tr style="background-color: #e8e8e8;">
                        <td style="padding: 8px; font-weight: bold; color: #555;">Email:</td>
                        <td style="padding: 8px;">{reservation.get('email', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold; color: #555;">Vehicle Number:</td>
                        <td style="padding: 8px;">{reservation.get('car_number', '')}</td>
                    </tr>
                    <tr style="background-color: #e8e8e8;">
                        <td style="padding: 8px; font-weight: bold; color: #555;">Vehicle Type:</td>
                        <td style="padding: 8px;">{reservation.get('space_type', '').upper()}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold; color: #555;">Parking Start:</td>
                        <td style="padding: 8px;">{reservation.get('start_datetime', '')}</td>
                    </tr>
                    <tr style="background-color: #e8e8e8;">
                        <td style="padding: 8px; font-weight: bold; color: #555;">Parking End:</td>
                        <td style="padding: 8px;">{reservation.get('end_datetime', '')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold; color: #555;">Reservation ID:</td>
                        <td style="padding: 8px;">#{reservation.get('id', '?')}</td>
                    </tr>
                    <tr style="background-color: #e8e8e8;">
                        <td style="padding: 8px; font-weight: bold; color: #555;">Timestamp:</td>
                        <td style="padding: 8px;">{created}</td>
                    </tr>
                </table>
                <div style="margin-top: 20px; padding: 15px; background-color: #FFF3E0; border-left: 4px solid #FF9800;">
                    <strong>⏳ Status: PENDING</strong><br>
                    This reservation is waiting for your review.
                </div>
                <p style="margin-top: 20px; color: #777;">
                    Review this reservation using the admin panel:<br>
                    <code>python main.py --admin</code>
                </p>
            </div>
        </body>
        </html>
        """

    # ──────────────────────────────────────────────────
    # User approval email builders
    # ──────────────────────────────────────────────────

    def _build_user_approval_text(self, reservation: Dict[str, Any]) -> str:
        approved_at = reservation.get("approved_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        notes = reservation.get("admin_notes", "")
        notes_line = f"  Admin Notes: {notes}\n" if notes else ""
        return (
            f"ParkSmart — Reservation Approved!\n"
            f"{'=' * 40}\n\n"
            f"Hi {reservation.get('first_name', '')},\n\n"
            f"Great news! Your reservation #{reservation.get('id', '?')} has been APPROVED.\n\n"
            f"Details:\n"
            f"  Vehicle: {reservation.get('car_number', '')}\n"
            f"  Space Type: {reservation.get('space_type', '').upper()}\n"
            f"  Start: {reservation.get('start_datetime', '')}\n"
            f"  End: {reservation.get('end_datetime', '')}\n"
            f"  Approved At: {approved_at}\n"
            f"{notes_line}\n"
            f"Parking Instructions:\n"
            f"  1. Enter via the main gate on 123 Main Street\n"
            f"  2. Show your reservation ID (#{reservation.get('id', '?')}) at the barrier\n"
            f"  3. Park in the designated {reservation.get('space_type', 'standard').upper()} area\n"
            f"  4. Display your vehicle registration visibly on the dashboard\n\n"
            f"Thank you for choosing ParkSmart!\n"
        )

    def _build_user_approval_html(self, reservation: Dict[str, Any]) -> str:
        approved_at = reservation.get("approved_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        notes = reservation.get("admin_notes", "")
        notes_html = f"<p><strong>Admin Notes:</strong> {notes}</p>" if notes else ""
        space = reservation.get("space_type", "standard").upper()
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #1B2A4A; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">🚗 ParkSmart</h1>
                <p style="color: #64B5F6; margin: 5px 0;">Reservation Confirmed</p>
            </div>
            <div style="padding: 20px; background-color: #f5f5f5;">
                <h2 style="color: #4CAF50;">Reservation #{reservation.get('id', '?')} — APPROVED ✅</h2>
                <p>Hi {reservation.get('first_name', '')},</p>
                <p>Great news! Your parking reservation has been approved.</p>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px; font-weight: bold;">Vehicle:</td>
                        <td style="padding: 8px;">{reservation.get('car_number', '')}</td>
                    </tr>
                    <tr style="background-color: #e8e8e8;">
                        <td style="padding: 8px; font-weight: bold;">Space Type:</td>
                        <td style="padding: 8px;">{space}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold;">Start:</td>
                        <td style="padding: 8px;">{reservation.get('start_datetime', '')}</td>
                    </tr>
                    <tr style="background-color: #e8e8e8;">
                        <td style="padding: 8px; font-weight: bold;">End:</td>
                        <td style="padding: 8px;">{reservation.get('end_datetime', '')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold;">Approved At:</td>
                        <td style="padding: 8px;">{approved_at}</td>
                    </tr>
                </table>
                {notes_html}
                <div style="margin-top: 20px; padding: 15px; background-color: #E8F5E9; border-left: 4px solid #4CAF50;">
                    <strong>🅿️ Parking Instructions</strong><br>
                    <ol style="margin: 10px 0; padding-left: 20px;">
                        <li>Enter via the main gate on 123 Main Street</li>
                        <li>Show your reservation ID (<strong>#{reservation.get('id', '?')}</strong>) at the barrier</li>
                        <li>Park in the designated <strong>{space}</strong> area</li>
                        <li>Display your vehicle registration visibly on the dashboard</li>
                    </ol>
                </div>
                <p style="margin-top: 15px; color: #777;">Thank you for choosing ParkSmart!</p>
            </div>
        </body>
        </html>
        """

    # ──────────────────────────────────────────────────
    # User rejection email builders
    # ──────────────────────────────────────────────────

    def _build_user_rejection_text(self, reservation: Dict[str, Any]) -> str:
        reason = reservation.get("admin_notes") or "No specific reason provided"
        return (
            f"ParkSmart — Reservation Update\n"
            f"{'=' * 40}\n\n"
            f"Hi {reservation.get('first_name', '')},\n\n"
            f"We regret to inform you that your reservation #{reservation.get('id', '?')} "
            f"could not be approved at this time.\n\n"
            f"Reason: {reason}\n\n"
            f"Reservation Details:\n"
            f"  Vehicle: {reservation.get('car_number', '')}\n"
            f"  Space Type: {reservation.get('space_type', '').upper()}\n"
            f"  Requested Period: {reservation.get('start_datetime', '')} → {reservation.get('end_datetime', '')}\n\n"
            f"You are welcome to submit a new reservation for a different time slot.\n"
            f"For assistance, contact our support team.\n\n"
            f"Thank you for your understanding.\n"
            f"— The ParkSmart Team\n"
        )

    def _build_user_rejection_html(self, reservation: Dict[str, Any]) -> str:
        reason = reservation.get("admin_notes") or "No specific reason provided"
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #1B2A4A; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">🚗 ParkSmart</h1>
                <p style="color: #64B5F6; margin: 5px 0;">Reservation Update</p>
            </div>
            <div style="padding: 20px; background-color: #f5f5f5;">
                <h2 style="color: #F44336;">Reservation #{reservation.get('id', '?')} — Not Approved</h2>
                <p>Hi {reservation.get('first_name', '')},</p>
                <p>We regret to inform you that your parking reservation could not be approved at this time.</p>
                <div style="margin: 15px 0; padding: 15px; background-color: #FFEBEE; border-left: 4px solid #F44336;">
                    <strong>Reason:</strong> {reason}
                </div>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px; font-weight: bold;">Vehicle:</td>
                        <td style="padding: 8px;">{reservation.get('car_number', '')}</td>
                    </tr>
                    <tr style="background-color: #e8e8e8;">
                        <td style="padding: 8px; font-weight: bold;">Space Type:</td>
                        <td style="padding: 8px;">{reservation.get('space_type', '').upper()}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold;">Requested Period:</td>
                        <td style="padding: 8px;">{reservation.get('start_datetime', '')} → {reservation.get('end_datetime', '')}</td>
                    </tr>
                </table>
                <p style="margin-top: 15px;">You are welcome to submit a new reservation for a different time slot.</p>
                <p style="color: #777;">Thank you for your understanding.<br>— The ParkSmart Team</p>
            </div>
        </body>
        </html>
        """
