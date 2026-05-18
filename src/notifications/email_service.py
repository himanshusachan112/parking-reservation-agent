"""
Email Notification Service - Notifies Admin of New Reservations.

This module sends email notifications to the parking administrator
when a new reservation request is submitted by a user.

WHY EMAIL?
The Stage 2 task says: "Chat bot should be able to send a reservation request
to administrator (e.g. via email server, messenger, rest api)."
Email is the most practical real-world notification channel.

HOW IT WORKS:
1. User completes reservation → saved to DB as 'pending'
2. REST API calls email_service.notify_new_reservation()
3. Email is sent to admin with reservation details
4. Admin reviews via the admin panel or REST API

CONFIGURATION:
Set these in your .env file:
  SMTP_HOST=smtp.gmail.com       (or your SMTP server)
  SMTP_PORT=587
  SMTP_USERNAME=your-email@gmail.com
  SMTP_PASSWORD=your-app-password
  ADMIN_EMAIL=admin@example.com

If SMTP is not configured, the service logs to console instead
(graceful fallback — the system works without email).
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
import os


class EmailService:
    """
    Email notification service for admin alerts.

    Sends formatted HTML emails when new reservations arrive.
    Falls back to console logging if SMTP is not configured.
    """

    def __init__(self):
        """
        Initialize email service with SMTP credentials from environment.

        If SMTP_HOST is not set, the service operates in 'console mode'
        and prints notifications instead of sending emails.
        """
        self.smtp_host = os.getenv("SMTP_HOST", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.admin_email = os.getenv("ADMIN_EMAIL", "admin@parksmart.com")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_username or "noreply@parksmart.com")

        # Check if SMTP is configured
        self.is_configured = bool(self.smtp_host and self.smtp_username and self.smtp_password)

        if self.is_configured:
            print(f"✓ Email service configured (SMTP: {self.smtp_host})")
        else:
            print("ℹ Email service in console mode (SMTP not configured)")

    def notify_new_reservation(self, reservation: Dict[str, Any]) -> bool:
        """
        Send a notification about a new reservation to the admin.

        Args:
            reservation: Dict with reservation details (id, name, car, etc.)

        Returns:
            True if notification was sent/logged successfully
        """
        if not self.is_configured:
            # Console fallback — print the notification
            return self._log_to_console(reservation)

        try:
            return self._send_email(reservation)
        except Exception as e:
            print(f"⚠ Email failed: {e}. Falling back to console.")
            return self._log_to_console(reservation)

    def notify_user_status_change(self, reservation: Dict[str, Any]) -> bool:
        """
        Notify the user that their reservation status has changed (approved/rejected).

        Sends an email to the user's email address if available, or logs to console.

        Args:
            reservation: Dict with reservation details including status and email

        Returns:
            True if notification was sent/logged successfully
        """
        user_email = reservation.get("email")
        status = reservation.get("status", "unknown")
        rid = reservation.get("id", "?")
        name = f"{reservation.get('first_name', '')} {reservation.get('last_name', '')}"

        if not user_email:
            print(f"ℹ No email for reservation #{rid} — skipping user notification.")
            return False

        if not self.is_configured:
            return self._log_user_notification_console(reservation)

        try:
            return self._send_user_notification_email(reservation)
        except Exception as e:
            print(f"⚠ User email failed: {e}. Falling back to console.")
            return self._log_user_notification_console(reservation)

    def _log_user_notification_console(self, reservation: Dict[str, Any]) -> bool:
        """Log user status-change notification to console (fallback)."""
        status = reservation.get("status", "unknown")
        status_emoji = "✅" if status == "approved" else "🚫"
        print("\n" + "=" * 50)
        print(f"  📧 USER NOTIFICATION (console mode)")
        print("=" * 50)
        print(f"  To: {reservation.get('email', 'N/A')}")
        print(f"  Reservation #{reservation.get('id', '?')} has been {status_emoji} {status.upper()}!")
        print(f"  Name: {reservation.get('first_name', '')} {reservation.get('last_name', '')}")
        print(f"  Vehicle: {reservation.get('car_number', '')}")
        print(f"  Space: {reservation.get('space_type', '')}")
        print(f"  Period: {reservation.get('start_datetime', '')} → {reservation.get('end_datetime', '')}")
        if reservation.get("admin_notes"):
            print(f"  Notes: {reservation.get('admin_notes')}")
        print("=" * 50 + "\n")
        return True

    def _send_user_notification_email(self, reservation: Dict[str, Any]) -> bool:
        """Send a status-change notification email to the user."""
        user_email = reservation.get("email")
        status = reservation.get("status", "unknown")
        rid = reservation.get("id", "?")

        status_text = "Approved ✅" if status == "approved" else "Rejected"
        subject = f"🚗 ParkSmart — Reservation #{rid} {status_text}"

        html_body = self._build_user_notification_html(reservation)
        plain_text = self._build_user_notification_text(reservation)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = user_email

        msg.attach(MIMEText(plain_text, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.sendmail(self.from_email, user_email, msg.as_string())

        print(f"✓ User notification sent to {user_email} for reservation #{rid}")
        return True

    def _build_user_notification_text(self, reservation: Dict[str, Any]) -> str:
        """Build plain text email for user notification."""
        status = reservation.get("status", "unknown")
        status_label = "APPROVED" if status == "approved" else "REJECTED"
        return (
            f"ParkSmart Reservation Update\n"
            f"{'=' * 40}\n\n"
            f"Hi {reservation.get('first_name', '')},\n\n"
            f"Your reservation #{reservation.get('id', '?')} has been {status_label}.\n\n"
            f"Details:\n"
            f"  Vehicle: {reservation.get('car_number', '')}\n"
            f"  Space Type: {reservation.get('space_type', '')}\n"
            f"  Start: {reservation.get('start_datetime', '')}\n"
            f"  End: {reservation.get('end_datetime', '')}\n"
            f"  Admin Notes: {reservation.get('admin_notes', 'None')}\n\n"
            f"Thank you for using ParkSmart!\n"
        )

    def _build_user_notification_html(self, reservation: Dict[str, Any]) -> str:
        """Build HTML email for user notification."""
        status = reservation.get("status", "unknown")
        if status == "approved":
            status_color = "#4CAF50"
            status_label = "APPROVED ✅"
            status_message = "Your parking space is confirmed! Please arrive on time."
        else:
            status_color = "#F44336"
            status_label = "REJECTED"
            status_message = "Unfortunately, your reservation could not be approved."

        admin_notes = reservation.get("admin_notes", "")
        notes_html = f'<p><strong>Admin Notes:</strong> {admin_notes}</p>' if admin_notes else ""

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #1B2A4A; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">🚗 ParkSmart</h1>
                <p style="color: #64B5F6; margin: 5px 0;">Reservation Update</p>
            </div>

            <div style="padding: 20px; background-color: #f5f5f5;">
                <h2 style="color: {status_color};">Reservation #{reservation.get('id', '?')} — {status_label}</h2>

                <p>Hi {reservation.get('first_name', '')},</p>
                <p>{status_message}</p>

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
                        <td style="padding: 8px; font-weight: bold;">Start:</td>
                        <td style="padding: 8px;">{reservation.get('start_datetime', '')}</td>
                    </tr>
                    <tr style="background-color: #e8e8e8;">
                        <td style="padding: 8px; font-weight: bold;">End:</td>
                        <td style="padding: 8px;">{reservation.get('end_datetime', '')}</td>
                    </tr>
                </table>

                {notes_html}
            </div>
        </body>
        </html>
        """

    def _send_email(self, reservation: Dict[str, Any]) -> bool:
        """
        Send an actual email via SMTP.

        Args:
            reservation: Reservation details dict

        Returns:
            True if email was sent successfully
        """
        subject = f"🚗 New Parking Reservation #{reservation.get('id', '?')} - Review Required"

        # Build HTML email body
        html_body = self._build_email_html(reservation)

        # Create the email message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = self.admin_email

        # Plain text fallback
        plain_text = self._build_email_text(reservation)
        msg.attach(MIMEText(plain_text, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        # Send via SMTP
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.sendmail(self.from_email, self.admin_email, msg.as_string())

        print(f"✓ Email notification sent to {self.admin_email} for reservation #{reservation.get('id')}")
        return True

    def _log_to_console(self, reservation: Dict[str, Any]) -> bool:
        """
        Log the notification to console (fallback when SMTP is not configured).

        Args:
            reservation: Reservation details dict

        Returns:
            Always True
        """
        print("\n" + "=" * 50)
        print("  📧 ADMIN NOTIFICATION (console mode)")
        print("=" * 50)
        print(f"  New reservation #{reservation.get('id', '?')} needs review!")
        print(f"  Name: {reservation.get('first_name', '')} {reservation.get('last_name', '')}")
        print(f"  Vehicle: {reservation.get('car_number', '')}")
        print(f"  Space: {reservation.get('space_type', '')}")
        print(f"  Period: {reservation.get('start_datetime', '')} → {reservation.get('end_datetime', '')}")
        print(f"  Status: {reservation.get('status', 'pending')}")
        print("=" * 50)
        print("  → Run 'python main.py --admin' to review")
        print("=" * 50 + "\n")
        return True

    def _build_email_text(self, reservation: Dict[str, Any]) -> str:
        """Build plain text email body."""
        return (
            f"New Parking Reservation Request\n"
            f"{'=' * 40}\n\n"
            f"Reservation ID: #{reservation.get('id', '?')}\n"
            f"Name: {reservation.get('first_name', '')} {reservation.get('last_name', '')}\n"
            f"Vehicle: {reservation.get('car_number', '')}\n"
            f"Space Type: {reservation.get('space_type', '')}\n"
            f"Start: {reservation.get('start_datetime', '')}\n"
            f"End: {reservation.get('end_datetime', '')}\n"
            f"Status: PENDING - Awaiting your review\n\n"
            f"Please review this reservation in the admin panel.\n"
        )

    def _build_email_html(self, reservation: Dict[str, Any]) -> str:
        """Build HTML email body with formatting."""
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
                        <td style="padding: 8px; font-weight: bold; color: #555;">Name:</td>
                        <td style="padding: 8px;">{reservation.get('first_name', '')} {reservation.get('last_name', '')}</td>
                    </tr>
                    <tr style="background-color: #e8e8e8;">
                        <td style="padding: 8px; font-weight: bold; color: #555;">Vehicle:</td>
                        <td style="padding: 8px;">{reservation.get('car_number', '')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold; color: #555;">Space Type:</td>
                        <td style="padding: 8px;">{reservation.get('space_type', '').upper()}</td>
                    </tr>
                    <tr style="background-color: #e8e8e8;">
                        <td style="padding: 8px; font-weight: bold; color: #555;">Start:</td>
                        <td style="padding: 8px;">{reservation.get('start_datetime', '')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold; color: #555;">End:</td>
                        <td style="padding: 8px;">{reservation.get('end_datetime', '')}</td>
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
