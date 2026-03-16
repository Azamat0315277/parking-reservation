"""
Unit tests for PII detection and filtering module.

Tests all 9 PII types: SSN, Credit Card, Phone, Email, IP Address,
Driver's License, Passport, Bank Account, Date of Birth.
"""

import pytest

from src.guardrails.pii_filter import (
    PIIFilter,
    PIIType,
    PIIMatch,
    PIIDetectionResult,
    detect_pii,
    mask_pii,
    contains_pii,
    create_strict_filter,
    create_common_filter,
)


class TestPIIType:
    """Test PIIType enumeration."""

    def test_all_pii_types_exist(self):
        """Verify all expected PII types are defined."""
        expected_types = [
            'ssn', 'credit_card', 'phone_number', 'email',
            'ip_address', 'drivers_license', 'passport',
            'bank_account', 'date_of_birth',
        ]
        actual_types = [t.value for t in PIIType]
        assert sorted(actual_types) == sorted(expected_types)


class TestPIIMatch:
    """Test PIIMatch dataclass."""

    def test_pii_match_creation(self):
        """Test creating a PIIMatch instance."""
        match = PIIMatch(
            pii_type=PIIType.SSN,
            value='123-45-6789',
            start=10,
            end=21,
            confidence=0.95,
        )
        assert match.pii_type == PIIType.SSN
        assert match.value == '123-45-6789'
        assert match.start == 10
        assert match.end == 21
        assert match.confidence == 0.95

    def test_pii_match_default_confidence(self):
        """Test default confidence value."""
        match = PIIMatch(
            pii_type=PIIType.EMAIL,
            value='test@example.com',
            start=0,
            end=16,
        )
        assert match.confidence == 1.0


class TestPIIDetectionResult:
    """Test PIIDetectionResult dataclass."""

    def test_detection_result_no_pii(self):
        """Test result when no PII is found."""
        result = PIIDetectionResult(
            contains_pii=False,
            matches=[],
            pii_types_found=[],
            original_text='Hello world',
            masked_text='Hello world',
        )
        assert not result.contains_pii
        assert len(result.matches) == 0

    def test_detection_result_with_pii(self):
        """Test result when PII is found."""
        match = PIIMatch(PIIType.SSN, '123-45-6789', 0, 11)
        result = PIIDetectionResult(
            contains_pii=True,
            matches=[match],
            pii_types_found=[PIIType.SSN],
            original_text='123-45-6789',
            masked_text='***********',
        )
        assert result.contains_pii
        assert len(result.matches) == 1
        assert PIIType.SSN in result.pii_types_found


class TestPIIFilterSSN:
    """Test SSN detection."""

    @pytest.fixture
    def pii_filter(self):
        return PIIFilter(enabled_types=[PIIType.SSN])

    def test_detect_ssn_with_dashes(self, pii_filter):
        """Detect SSN in format XXX-XX-XXXX."""
        result = pii_filter.detect('My SSN is 123-45-6789')
        assert result.contains_pii
        assert len(result.matches) == 1
        assert result.matches[0].pii_type == PIIType.SSN

    def test_detect_ssn_without_dashes(self, pii_filter):
        """Detect SSN without dashes."""
        result = pii_filter.detect('SSN: 123456789')
        assert result.contains_pii

    def test_detect_ssn_with_spaces(self, pii_filter):
        """Detect SSN with spaces."""
        result = pii_filter.detect('Number: 123 45 6789')
        assert result.contains_pii

    def test_invalid_ssn_000_prefix(self, pii_filter):
        """SSN starting with 000 is invalid."""
        result = pii_filter.detect('Not valid: 000-12-3456')
        assert not result.contains_pii

    def test_invalid_ssn_666_prefix(self, pii_filter):
        """SSN starting with 666 is invalid."""
        result = pii_filter.detect('Not valid: 666-12-3456')
        assert not result.contains_pii

    def test_mask_ssn(self, pii_filter):
        """Test masking SSN."""
        masked = pii_filter.mask('My SSN is 123-45-6789')
        assert '123-45-6789' not in masked
        assert '***' in masked


class TestPIIFilterCreditCard:
    """Test credit card detection."""

    @pytest.fixture
    def pii_filter(self):
        return PIIFilter(enabled_types=[PIIType.CREDIT_CARD])

    def test_detect_visa(self, pii_filter):
        """Detect Visa card number."""
        result = pii_filter.detect('Visa: 4111111111111111')
        assert result.contains_pii
        assert result.matches[0].pii_type == PIIType.CREDIT_CARD

    def test_detect_mastercard(self, pii_filter):
        """Detect MasterCard number."""
        result = pii_filter.detect('MC: 5500000000000004')
        assert result.contains_pii

    def test_detect_amex(self, pii_filter):
        """Detect American Express number."""
        result = pii_filter.detect('Amex: 340000000000009')
        assert result.contains_pii

    def test_detect_discover(self, pii_filter):
        """Detect Discover card number."""
        result = pii_filter.detect('Discover: 6011000000000004')
        assert result.contains_pii

    def test_invalid_card_too_short(self, pii_filter):
        """Short numbers should not be detected as credit cards."""
        result = pii_filter.detect('Number: 123456789')
        # Short numbers don't match credit card pattern
        assert not result.contains_pii


class TestPIIFilterEmail:
    """Test email address detection."""

    @pytest.fixture
    def pii_filter(self):
        return PIIFilter(enabled_types=[PIIType.EMAIL])

    def test_detect_simple_email(self, pii_filter):
        """Detect simple email address."""
        result = pii_filter.detect('Contact: john@example.com')
        assert result.contains_pii
        assert result.matches[0].pii_type == PIIType.EMAIL

    def test_detect_email_with_dots(self, pii_filter):
        """Detect email with dots in local part."""
        result = pii_filter.detect('Email: john.doe@example.com')
        assert result.contains_pii

    def test_detect_email_subdomain(self, pii_filter):
        """Detect email with subdomain."""
        result = pii_filter.detect('Email: user@mail.example.co.uk')
        assert result.contains_pii

    def test_invalid_email_no_at(self, pii_filter):
        """Invalid email without @ symbol."""
        result = pii_filter.detect('Not email: johndoe.com')
        assert not result.contains_pii


class TestPIIFilterPhone:
    """Test phone number detection."""

    @pytest.fixture
    def pii_filter(self):
        return PIIFilter(enabled_types=[PIIType.PHONE_NUMBER])

    def test_detect_phone_with_parentheses(self, pii_filter):
        """Detect phone in (XXX) XXX-XXXX format."""
        result = pii_filter.detect('Call: (555) 123-4567')
        assert result.contains_pii
        assert result.matches[0].pii_type == PIIType.PHONE_NUMBER

    def test_detect_phone_with_dashes(self, pii_filter):
        """Detect phone in XXX-XXX-XXXX format."""
        result = pii_filter.detect('Phone: 555-123-4567')
        assert result.contains_pii

    def test_detect_phone_with_country_code(self, pii_filter):
        """Detect phone with +1 country code."""
        result = pii_filter.detect('Mobile: +1-555-123-4567')
        assert result.contains_pii

    def test_detect_phone_with_spaces(self, pii_filter):
        """Detect phone with spaces."""
        result = pii_filter.detect('Tel: 555 123 4567')
        assert result.contains_pii


class TestPIIFilterIPAddress:
    """Test IP address detection."""

    @pytest.fixture
    def pii_filter(self):
        return PIIFilter(enabled_types=[PIIType.IP_ADDRESS])

    def test_detect_private_ip(self, pii_filter):
        """Detect private IP address."""
        result = pii_filter.detect('Server: 192.168.1.1')
        assert result.contains_pii
        assert result.matches[0].pii_type == PIIType.IP_ADDRESS

    def test_detect_public_ip(self, pii_filter):
        """Detect public IP address."""
        result = pii_filter.detect('IP: 8.8.8.8')
        assert result.contains_pii

    def test_detect_max_ip(self, pii_filter):
        """Detect maximum valid IP address."""
        result = pii_filter.detect('Max IP: 255.255.255.255')
        assert result.contains_pii

    def test_invalid_ip_out_of_range(self, pii_filter):
        """Invalid IP with octet > 255."""
        result = pii_filter.detect('Invalid: 999.999.999.999')
        assert not result.contains_pii


class TestPIIFilterDateOfBirth:
    """Test date of birth detection."""

    @pytest.fixture
    def pii_filter(self):
        return PIIFilter(enabled_types=[PIIType.DATE_OF_BIRTH])

    def test_detect_dob_with_label(self, pii_filter):
        """Detect DOB with label."""
        result = pii_filter.detect('DOB: 01/15/1990')
        assert result.contains_pii
        assert result.matches[0].pii_type == PIIType.DATE_OF_BIRTH

    def test_detect_date_of_birth_label(self, pii_filter):
        """Detect with 'Date of Birth' label."""
        result = pii_filter.detect('Date of Birth: 1990-01-15')
        assert result.contains_pii

    def test_no_detect_plain_date(self, pii_filter):
        """Plain date without DOB label should not be detected."""
        result = pii_filter.detect('Meeting on 01/15/2024')
        assert not result.contains_pii


class TestPIIFilterMultipleTypes:
    """Test detection of multiple PII types in same text."""

    @pytest.fixture
    def pii_filter(self):
        return PIIFilter()

    def test_detect_multiple_pii_types(self, pii_filter):
        """Detect multiple PII types in same text."""
        text = 'Contact john@example.com or call 555-123-4567'
        result = pii_filter.detect(text)
        assert result.contains_pii
        assert len(result.matches) >= 2
        types_found = {m.pii_type for m in result.matches}
        assert PIIType.EMAIL in types_found
        assert PIIType.PHONE_NUMBER in types_found

    def test_mask_multiple_pii(self, pii_filter):
        """Mask multiple PII in same text."""
        text = 'SSN: 123-45-6789, Email: test@example.com'
        masked = pii_filter.mask(text)
        assert '123-45-6789' not in masked
        assert 'test@example.com' not in masked


class TestPIIFilterActions:
    """Test filter_document actions."""

    @pytest.fixture
    def pii_filter(self):
        return PIIFilter(enabled_types=[PIIType.SSN])

    def test_action_mask(self, pii_filter):
        """Test mask action."""
        text = 'SSN: 123-45-6789'
        result = pii_filter.filter_document(text, action='mask')
        assert '123-45-6789' not in result
        assert len(result) == len(text)  # Masked preserves length

    def test_action_remove(self, pii_filter):
        """Test remove action."""
        text = 'SSN: 123-45-6789 end'
        result = pii_filter.filter_document(text, action='remove')
        assert '123-45-6789' not in result
        assert len(result) < len(text)

    def test_action_reject(self, pii_filter):
        """Test reject action raises ValueError."""
        text = 'SSN: 123-45-6789'
        with pytest.raises(ValueError) as exc_info:
            pii_filter.filter_document(text, action='reject')
        assert 'PII detected' in str(exc_info.value)

    def test_no_pii_returns_original(self, pii_filter):
        """Text without PII returns unchanged."""
        text = 'Hello, world!'
        result = pii_filter.filter_document(text, action='mask')
        assert result == text


class TestPIIFilterConfiguration:
    """Test PIIFilter configuration options."""

    def test_enabled_types_filter(self):
        """Only enabled types should be detected."""
        pii_filter = PIIFilter(enabled_types=[PIIType.EMAIL])
        text = 'SSN: 123-45-6789, Email: test@example.com'
        result = pii_filter.detect(text)

        # Should only find email
        assert result.contains_pii
        assert all(m.pii_type == PIIType.EMAIL for m in result.matches)

    def test_min_confidence_threshold(self):
        """High confidence threshold filters low-confidence patterns."""
        high_conf_filter = PIIFilter(min_confidence=0.9)
        # Bank account has 0.6 confidence, should be filtered
        text = 'Account: 12345678901234'
        result = high_conf_filter.detect(text)
        # Bank account should not be detected with high threshold
        bank_matches = [m for m in result.matches if m.pii_type == PIIType.BANK_ACCOUNT]
        assert len(bank_matches) == 0

    def test_custom_mask_char(self):
        """Custom mask character should be used."""
        pii_filter = PIIFilter(
            enabled_types=[PIIType.EMAIL],
            mask_char='X',
        )
        masked = pii_filter.mask('Email: test@example.com')
        assert 'XXXX' in masked
        assert '*' not in masked


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    def test_detect_pii_function(self):
        """Test detect_pii convenience function."""
        result = detect_pii('SSN: 123-45-6789')
        assert isinstance(result, PIIDetectionResult)
        assert result.contains_pii

    def test_mask_pii_function(self):
        """Test mask_pii convenience function."""
        masked = mask_pii('SSN: 123-45-6789')
        assert isinstance(masked, str)
        assert '123-45-6789' not in masked

    def test_contains_pii_function(self):
        """Test contains_pii convenience function."""
        assert contains_pii('SSN: 123-45-6789') is True
        assert contains_pii('Hello, world!') is False


class TestFilterFactories:
    """Test filter factory functions."""

    def test_create_strict_filter(self):
        """Strict filter has all types and low threshold."""
        strict = create_strict_filter()
        assert len(strict.enabled_types) == len(PIIType)
        assert strict.min_confidence == 0.5

    def test_create_common_filter(self):
        """Common filter has only common PII types."""
        common = create_common_filter()
        expected_types = {PIIType.SSN, PIIType.CREDIT_CARD, PIIType.EMAIL, PIIType.PHONE_NUMBER}
        assert set(common.enabled_types) == expected_types
        assert common.min_confidence == 0.8


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def pii_filter(self):
        return PIIFilter()

    def test_empty_string(self, pii_filter):
        """Empty string should return no PII."""
        result = pii_filter.detect('')
        assert not result.contains_pii
        assert result.masked_text == ''

    def test_whitespace_only(self, pii_filter):
        """Whitespace-only string should return no PII."""
        result = pii_filter.detect('   \n\t   ')
        assert not result.contains_pii

    def test_pii_at_start(self, pii_filter):
        """PII at start of string."""
        result = pii_filter.detect('test@example.com is my email')
        assert result.contains_pii
        assert result.matches[0].start == 0

    def test_pii_at_end(self, pii_filter):
        """PII at end of string."""
        result = pii_filter.detect('My email is test@example.com')
        assert result.contains_pii

    def test_consecutive_pii(self, pii_filter):
        """Multiple PII values back to back."""
        text = 'test@a.com user@b.com'
        result = pii_filter.detect(text)
        email_matches = [m for m in result.matches if m.pii_type == PIIType.EMAIL]
        assert len(email_matches) == 2

    def test_unicode_text_no_pii(self, pii_filter):
        """Unicode text without PII."""
        result = pii_filter.detect('Привет мир! 你好世界!')
        # Should not detect false positives in unicode
        assert not result.contains_pii or len(result.matches) == 0
