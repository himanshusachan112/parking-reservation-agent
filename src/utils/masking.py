"""
Masking Utilities — Protect PII in terminal output and logs.

Functions to mask sensitive data (emails, etc.) before displaying
to terminal, logs, or UI. The original values are preserved internally
for actual notification delivery.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Precompiled regex for basic email format validation
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def mask_email(email: str) -> str:
    """
    Mask an email address for safe display in terminal/UI/logs.

    Preserves the first 2 characters of the local part and replaces
    the rest with asterisks.  The full domain is kept visible.

    Args:
        email: The email address to mask.

    Returns:
        The masked email string.

    Examples:
        >>> mask_email("sanyam@gmail.com")
        'sa****@gmail.com'
        >>> mask_email("ab@gmail.com")
        'ab***@gmail.com'
        >>> mask_email("a@example.com")
        'a***@example.com'
        >>> mask_email("")
        '***'
    """
    if not email or "@" not in email:
        return "***"

    local, domain = email.rsplit("@", 1)

    if len(local) <= 2:
        visible = local
    else:
        visible = local[:2]

    # Always show at least 3 asterisks so the mask is visually clear
    hidden_len = max(3, len(local) - 2)
    masked_local = visible + "*" * hidden_len

    return f"{masked_local}@{domain}"


def validate_email(email: str) -> bool:
    """
    Validate that a string looks like a well-formed email address.

    Uses a simple regex check — not a full RFC-5322 validator, but
    sufficient for user-facing input validation.

    Args:
        email: The string to validate.

    Returns:
        True if the string matches a basic email pattern.
    """
    if not email:
        return False
    return bool(_EMAIL_RE.match(email.strip()))
