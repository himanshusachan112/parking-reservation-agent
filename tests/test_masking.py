"""
Tests for the masking utility module.

Covers:
- Standard email masking
- Short username masking
- Empty / invalid input handling
- Email validation
"""

import pytest

from src.utils.masking import mask_email, validate_email


class TestMaskEmail:
    """Tests for mask_email()."""

    def test_standard_email(self):
        """Standard email: first 2 chars visible, rest masked."""
        assert mask_email("sanyam@gmail.com") == "sa****@gmail.com"

    def test_short_username_two_chars(self):
        """Username with exactly 2 chars: both visible + 3 asterisks."""
        assert mask_email("ab@gmail.com") == "ab***@gmail.com"

    def test_short_username_one_char(self):
        """Username with 1 char: visible + 3 asterisks."""
        assert mask_email("a@example.com") == "a***@example.com"

    def test_long_username(self):
        """Longer username: first 2 visible, rest masked."""
        result = mask_email("longusername@company.org")
        assert result.startswith("lo")
        assert result.endswith("@company.org")
        assert "longusername" not in result

    def test_empty_string(self):
        """Empty string returns '***'."""
        assert mask_email("") == "***"

    def test_none_input(self):
        """None returns '***'."""
        assert mask_email(None) == "***"

    def test_no_at_sign(self):
        """String without @ returns '***'."""
        assert mask_email("notanemail") == "***"

    def test_domain_preserved(self):
        """Full domain is always visible."""
        result = mask_email("test@subdomain.example.co.uk")
        assert result.endswith("@subdomain.example.co.uk")

    def test_three_char_username(self):
        """Username with 3 chars: 2 visible + 3 asterisks."""
        assert mask_email("abc@test.com") == "ab***@test.com"


class TestValidateEmail:
    """Tests for validate_email()."""

    def test_valid_email(self):
        assert validate_email("user@example.com") is True

    def test_valid_email_with_dots(self):
        assert validate_email("first.last@company.co.uk") is True

    def test_valid_email_with_plus(self):
        assert validate_email("user+tag@gmail.com") is True

    def test_invalid_no_at(self):
        assert validate_email("noatsign.com") is False

    def test_invalid_no_domain(self):
        assert validate_email("user@") is False

    def test_invalid_empty(self):
        assert validate_email("") is False

    def test_invalid_none(self):
        assert validate_email(None) is False

    def test_invalid_spaces(self):
        assert validate_email("user @test.com") is False
