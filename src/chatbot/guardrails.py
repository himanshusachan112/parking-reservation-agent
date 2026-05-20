"""
Guardrails Module - Data Protection and Safety Filtering.

This module implements two types of protection:

1. INPUT GUARDRAILS (check_input):
   - Detects prompt injection attempts (users trying to override system instructions)
   - Blocks requests for other users' personal information
   - Prevents malicious queries

2. OUTPUT GUARDRAILS (filter_output):
   - Scans LLM responses for accidentally leaked PII
   - Redacts any sensitive information (phone numbers, emails, card numbers)
   - Ensures no internal system details are exposed

HOW PII DETECTION WORKS:
- Uses Microsoft Presidio, which combines:
  * Named Entity Recognition (NER) - ML models trained to find names, orgs, etc.
  * Pattern matching - Regex for structured data (phone, email, SSN)
  * Context analysis - Checks surrounding words (e.g., "call me at" before a number)

- Each detection has a confidence score (0.0 to 1.0)
- We only act on detections above our threshold (default: 0.7)

ALTERNATIVE APPROACH (fallback if Presidio is not available):
- Simple regex-based detection for common PII patterns
- Less accurate but works without extra model downloads
"""

import re
from typing import Any, Dict, List

from config.settings import settings


class Guardrails:
    """
    Guardrails for protecting sensitive data and preventing misuse.

    Uses a dual approach:
    - Presidio NLP analyzer (if available) for high-accuracy PII detection
    - Regex fallback patterns for basic protection
    """

    def __init__(self):
        """Initialize the guardrails with PII detection capabilities."""
        self.enabled = settings.guardrails_enabled
        self.confidence_threshold = settings.pii_confidence_threshold

        # Try to load Presidio (NLP-based PII detection)
        self.presidio_available = False
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_anonymizer import AnonymizerEngine

            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
            self.presidio_available = True
            print("✓ Presidio PII analyzer loaded successfully.")
        except (ImportError, Exception) as e:
            print(f"⚠ Presidio not available, using regex fallback. Reason: {e}")

        # Keywords that suggest a prompt injection attempt
        self.injection_patterns = [
            r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions|rules|prompts)",
            r"ignore\s+(previous|all|above)\s+(instructions|rules|prompts)",
            r"forget\s+(everything|all|your)\s*(instructions|rules|training)?",
            r"you\s+are\s+now\s+(?!parksmart)",  # "you are now DAN/evil" etc.
            r"override\s+(system|safety|your)\s*(prompt|rules|instructions)?",
            r"pretend\s+you\s+(are|don't\s+have)",
            r"reveal\s+(your|the)\s+(system|initial|original)\s*(prompt|instructions)?",
            r"show\s+me\s+(your|the)\s+(system|initial)\s*prompt",
            r"what\s+(is|are)\s+your\s+(system|initial)\s*(prompt|instructions)",
        ]

        # Keywords suggesting request for other users' data
        self.data_request_patterns = [
            r"show\s+me\s+(all\s+)?(other\s+)?(users?'?s?|customers?'?s?)\s*(reservations?|bookings?|data|info)?",
            r"show\s+me\s+all\s+other\s+",
            r"(list|give|tell)\s+me\s+.*(other|all)\s*(people|users?|customers?)",
            r"list\s+all\s+(customers?|users?|bookings?|reservations?)",
            r"who\s+(else\s+)?(has|made|booked)\s+",
            r"(database|db|table|record)\s*(dump|export|contents?|data)",
            r"(admin|administrator|internal)\s*(password|access|credentials?)",
        ]

        # Regex patterns for PII detection (fallback)
        self.pii_patterns = {
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "phone": r"\b(\+?1?[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
            "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
            "ssn": r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",
        }

        # Known safe patterns (parking-related data that looks like PII but isn't)
        self.safe_patterns = [
            r"\+1-555-PARK-123",  # Our own phone number
            r"support@parksmart\.com",  # Our own email
            r"reservations@parksmart\.com",
            r"feedback@parksmart\.com",
            r"[A-Za-z0-9]{1,2}\*{2,}@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",  # Masked emails (e.g. sa****@gmail.com)
        ]

    def check_input(self, user_input: str) -> Dict[str, Any]:
        """
        Check user input for malicious content.

        Checks for:
        1. Prompt injection attempts
        2. Requests for other users' private data

        Args:
            user_input: The raw user message

        Returns:
            Dict with:
            - blocked: bool (True if message should be blocked)
            - reason: str (why it was blocked, if applicable)
            - message: str (response to send to user if blocked)
        """
        if not self.enabled:
            return {"blocked": False, "reason": None, "message": None}

        # Ensure input is a plain string
        user_input = str(user_input)
        input_lower = user_input.lower()

        # Check for prompt injection
        for pattern in self.injection_patterns:
            if re.search(pattern, input_lower):
                return {
                    "blocked": True,
                    "reason": "prompt_injection",
                    "message": (
                        "I'm sorry, but I can only help with parking-related queries "
                        "such as information about our facility, pricing, availability, "
                        "and making reservations. How can I assist you today?"
                    ),
                }

        # Check for requests for other users' data
        for pattern in self.data_request_patterns:
            if re.search(pattern, input_lower):
                return {
                    "blocked": True,
                    "reason": "data_privacy",
                    "message": (
                        "I'm sorry, I cannot share other users' personal information "
                        "or reservation details. I can only help you with your own "
                        "reservation or provide general parking information. "
                        "How else can I help you?"
                    ),
                }

        return {"blocked": False, "reason": None, "message": None}

    def filter_output(self, response: str) -> str:
        """
        Filter the LLM output to remove any accidentally leaked PII.

        This is a safety net - even if the LLM somehow includes sensitive
        data in its response, this function catches and redacts it.

        Args:
            response: The raw LLM response

        Returns:
            Filtered response with PII redacted
        """
        if not self.enabled:
            return response

        # Ensure response is a plain string
        response = str(response) if not isinstance(response, str) else response

        # First, check if any patterns are in the "safe" list (our own contact info)
        # These should not be redacted
        safe_matches = []
        for pattern in self.safe_patterns:
            for match in re.finditer(pattern, response):
                safe_matches.append((match.start(), match.end()))

        # Use Presidio if available (more accurate)
        if self.presidio_available:
            return self._filter_with_presidio(response, safe_matches)

        # Otherwise, use regex fallback
        return self._filter_with_regex(response, safe_matches)

    def _filter_with_presidio(self, text: str, safe_ranges: List[tuple]) -> str:
        """
        Use Presidio NLP analyzer to detect and redact PII.

        Presidio detects: names, emails, phones, credit cards,
        addresses, SSNs, and many more entity types.
        """
        from presidio_analyzer import AnalyzerEngine

        # Analyze the text for PII entities
        results = self.analyzer.analyze(
            text=text,
            language="en",
            entities=[
                "PHONE_NUMBER",
                "EMAIL_ADDRESS",
                "CREDIT_CARD",
                "US_SSN",
                "IBAN_CODE",
                "IP_ADDRESS",
            ],
            score_threshold=self.confidence_threshold,
        )

        # Filter out detections that fall within "safe" ranges
        filtered_results = []
        for result in results:
            is_safe = any(safe_start <= result.start and result.end <= safe_end for safe_start, safe_end in safe_ranges)
            if not is_safe:
                filtered_results.append(result)

        # If no PII found, return as-is
        if not filtered_results:
            return text

        # Redact detected PII
        anonymized = self.anonymizer.anonymize(
            text=text,
            analyzer_results=filtered_results,
        )

        return anonymized.text

    def _filter_with_regex(self, text: str, safe_ranges: List[tuple]) -> str:
        """
        Fallback: Use regex patterns to detect and redact PII.
        Less accurate than Presidio but works without extra dependencies.
        """
        filtered_text = text

        for pii_type, pattern in self.pii_patterns.items():
            for match in re.finditer(pattern, filtered_text):
                # Check if this match is in a safe range
                is_safe = any(
                    safe_start <= match.start() and match.end() <= safe_end for safe_start, safe_end in safe_ranges
                )

                if not is_safe:
                    # Replace with redaction marker
                    redacted = f"[{pii_type.upper()}_REDACTED]"
                    filtered_text = filtered_text[: match.start()] + redacted + filtered_text[match.end() :]
                    # Recalculate safe_ranges offset (text length changed)
                    break  # Start over to handle offset changes

        return filtered_text

    def detect_pii_in_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect PII entities in text (for evaluation/debugging).

        Returns a list of detected entities with their types and positions.
        Useful for testing the guardrails system.
        """
        if self.presidio_available:
            results = self.analyzer.analyze(
                text=text,
                language="en",
                score_threshold=self.confidence_threshold,
            )
            return [
                {
                    "entity_type": r.entity_type,
                    "start": r.start,
                    "end": r.end,
                    "score": r.score,
                    "text": text[r.start : r.end],
                }
                for r in results
            ]
        else:
            # Regex-based detection
            detections = []
            for pii_type, pattern in self.pii_patterns.items():
                for match in re.finditer(pattern, text):
                    detections.append(
                        {
                            "entity_type": pii_type.upper(),
                            "start": match.start(),
                            "end": match.end(),
                            "score": 1.0,
                            "text": match.group(),
                        }
                    )
            return detections
