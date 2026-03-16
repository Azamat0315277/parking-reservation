"""
PII (Personally Identifiable Information) detection and filtering module.

Provides programmatic guardrails to detect and mask sensitive data
before storing in vector databases or transmitting to external services.

Supports detection of:
- Social Security Numbers (SSN)
- Credit/Debit Card Numbers
- Phone Numbers (US formats)
- Email Addresses
- IP Addresses
- Driver's License Numbers
- Passport Numbers
- Bank Account Numbers
- Date of Birth patterns
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class PIIType(Enum):
    """Types of PII that can be detected."""
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    PHONE_NUMBER = "phone_number"
    EMAIL = "email"
    IP_ADDRESS = "ip_address"
    DRIVERS_LICENSE = "drivers_license"
    PASSPORT = "passport"
    BANK_ACCOUNT = "bank_account"
    DATE_OF_BIRTH = "date_of_birth"


@dataclass
class PIIMatch:
    """Represents a single PII match found in text."""
    pii_type: PIIType
    value: str
    start: int
    end: int
    confidence: float = 1.0


@dataclass
class PIIDetectionResult:
    """Result of PII detection on a text."""
    contains_pii: bool
    matches: List[PIIMatch] = field(default_factory=list)
    pii_types_found: List[PIIType] = field(default_factory=list)
    original_text: str = ""
    masked_text: str = ""


class PIIFilter:
    """
    PII detection and filtering using regex patterns.

    This class provides methods to detect, mask, and filter PII
    from text before it is stored in vector databases or processed.
    """

    # Regex patterns for PII detection
    PATTERNS: Dict[PIIType, Tuple[str, float]] = {
        # SSN: XXX-XX-XXXX or XXXXXXXXX
        PIIType.SSN: (
            r'\b(?!000|666|9\d{2})([0-8]\d{2}|7([0-6]\d|7[012]))'
            r'[-\s]?(?!00)\d{2}[-\s]?(?!0000)\d{4}\b',
            0.95
        ),

        # Credit Card Numbers (Visa, MasterCard, Amex, Discover)
        PIIType.CREDIT_CARD: (
            r'\b(?:4[0-9]{12}(?:[0-9]{3})?|'  # Visa
            r'5[1-5][0-9]{14}|'  # MasterCard
            r'3[47][0-9]{13}|'  # Amex
            r'6(?:011|5[0-9]{2})[0-9]{12}|'  # Discover
            r'(?:2131|1800|35\d{3})\d{11})'  # JCB
            r'(?:[-\s]?\d{4}){0,3}\b',
            0.90
        ),

        # Phone Numbers (various US formats)
        PIIType.PHONE_NUMBER: (
            r'\b(?:\+?1[-.\s]?)?'
            r'(?:\(?\d{3}\)?[-.\s]?)'
            r'\d{3}[-.\s]?\d{4}\b',
            0.85
        ),

        # Email Addresses
        PIIType.EMAIL: (
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            0.95
        ),

        # IP Addresses (IPv4)
        PIIType.IP_ADDRESS: (
            r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
            r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
            0.90
        ),

        # Driver's License (generic patterns - varies by state)
        PIIType.DRIVERS_LICENSE: (
            r'\b[A-Z]{1,2}[-\s]?\d{5,8}\b',
            0.70
        ),

        # Passport Numbers (US format)
        PIIType.PASSPORT: (
            r'\b[A-Z]{1,2}\d{6,9}\b',
            0.70
        ),

        # Bank Account Numbers (generic)
        PIIType.BANK_ACCOUNT: (
            r'\b\d{8,17}\b',
            0.60
        ),

        # Date of Birth patterns (MM/DD/YYYY, YYYY-MM-DD, etc.)
        PIIType.DATE_OF_BIRTH: (
            r'\b(?:DOB|D\.O\.B\.|Date of Birth|Birth Date)[\s:]*'
            r'(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})\b',
            0.85
        ),
    }

    # Default mask character
    MASK_CHAR = '*'

    def __init__(
        self,
        enabled_types: Optional[List[PIIType]] = None,
        min_confidence: float = 0.7,
        mask_char: str = '*',
    ):
        """
        Initialize PII filter.

        Args:
            enabled_types: List of PII types to detect (default: all)
            min_confidence: Minimum confidence threshold for matches
            mask_char: Character to use for masking PII
        """
        self.enabled_types = enabled_types or list(PIIType)
        self.min_confidence = min_confidence
        self.mask_char = mask_char

        # Compile regex patterns
        self._compiled_patterns: Dict[PIIType, re.Pattern] = {}
        for pii_type in self.enabled_types:
            if pii_type in self.PATTERNS:
                pattern, _ = self.PATTERNS[pii_type]
                self._compiled_patterns[pii_type] = re.compile(
                    pattern, re.IGNORECASE
                )

    def detect(self, text: str) -> PIIDetectionResult:
        """
        Detect PII in the given text.

        Args:
            text: Text to scan for PII

        Returns:
            PIIDetectionResult with all matches found
        """
        matches = []
        pii_types_found = set()

        for pii_type, pattern in self._compiled_patterns.items():
            _, confidence = self.PATTERNS[pii_type]

            if confidence < self.min_confidence:
                continue

            for match in pattern.finditer(text):
                pii_match = PIIMatch(
                    pii_type=pii_type,
                    value=match.group(),
                    start=match.start(),
                    end=match.end(),
                    confidence=confidence,
                )
                matches.append(pii_match)
                pii_types_found.add(pii_type)

        # Sort matches by position
        matches.sort(key=lambda m: m.start)

        # Generate masked text
        masked_text = self._mask_text(text, matches)

        return PIIDetectionResult(
            contains_pii=len(matches) > 0,
            matches=matches,
            pii_types_found=list(pii_types_found),
            original_text=text,
            masked_text=masked_text,
        )

    def _mask_text(self, text: str, matches: List[PIIMatch]) -> str:
        """
        Mask PII in text based on detected matches.

        Args:
            text: Original text
            matches: List of PII matches to mask

        Returns:
            Text with PII masked
        """
        if not matches:
            return text

        # Build masked text by replacing matches
        result = []
        last_end = 0

        for match in matches:
            # Add text before the match
            result.append(text[last_end:match.start])
            # Add masked value (preserve length)
            mask_length = match.end - match.start
            result.append(self.mask_char * mask_length)
            last_end = match.end

        # Add remaining text
        result.append(text[last_end:])

        return ''.join(result)

    def mask(self, text: str) -> str:
        """
        Mask all PII in the given text.

        Args:
            text: Text containing PII

        Returns:
            Text with PII masked
        """
        result = self.detect(text)
        return result.masked_text

    def contains_pii(self, text: str) -> bool:
        """
        Check if text contains any PII.

        Args:
            text: Text to check

        Returns:
            True if PII is detected, False otherwise
        """
        result = self.detect(text)
        return result.contains_pii

    def filter_document(self, text: str, action: str = "mask") -> str:
        """
        Filter a document by detecting and handling PII.

        Args:
            text: Document text
            action: Action to take - "mask" (default), "remove", or "reject"

        Returns:
            Filtered text (or raises ValueError if action is "reject" and PII found)

        Raises:
            ValueError: If action is "reject" and PII is detected
        """
        result = self.detect(text)

        if not result.contains_pii:
            return text

        if action == "reject":
            pii_types = [t.value for t in result.pii_types_found]
            raise ValueError(
                f"PII detected in document: {', '.join(pii_types)}. "
                f"Found {len(result.matches)} instances."
            )
        elif action == "remove":
            # Remove PII entirely (replace with empty string)
            filtered = text
            for match in reversed(result.matches):
                filtered = filtered[:match.start] + filtered[match.end:]
            return filtered
        else:  # mask
            return result.masked_text


# Convenience functions for quick PII detection

_default_filter = PIIFilter()


def detect_pii(text: str) -> PIIDetectionResult:
    """Detect PII in text using default filter."""
    return _default_filter.detect(text)


def mask_pii(text: str) -> str:
    """Mask PII in text using default filter."""
    return _default_filter.mask(text)


def contains_pii(text: str) -> bool:
    """Check if text contains PII using default filter."""
    return _default_filter.contains_pii(text)


# High-sensitivity filter for stricter detection
def create_strict_filter() -> PIIFilter:
    """Create a strict PII filter with all types enabled and low threshold."""
    return PIIFilter(
        enabled_types=list(PIIType),
        min_confidence=0.5,
    )


# Filter for common PII types only
def create_common_filter() -> PIIFilter:
    """Create a filter for most common PII types (SSN, CC, email, phone)."""
    return PIIFilter(
        enabled_types=[
            PIIType.SSN,
            PIIType.CREDIT_CARD,
            PIIType.EMAIL,
            PIIType.PHONE_NUMBER,
        ],
        min_confidence=0.8,
    )
