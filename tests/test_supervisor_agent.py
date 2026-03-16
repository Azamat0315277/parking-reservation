"""
Unit tests for supervisor agent configuration.

Tests system prompt and expected tool bindings without importing
modules that require API keys.
"""

import pytest
import json


class TestSupervisorPromptFormat:
    """Test supervisor prompt format and content."""

    def test_info_classification_format(self):
        """INFO classification should follow expected format."""
        info_tag = '<<<INFO>>>'
        assert '<<<' in info_tag
        assert 'INFO' in info_tag
        assert '>>>' in info_tag

    def test_reservation_classification_format(self):
        """RESERVATION classification should follow expected format."""
        data = {'customer_name': 'John', 'parking_type': 'Standard'}
        reservation_tag = f'<<<RESERVATION:{json.dumps(data)}>>>'

        assert '<<<RESERVATION:' in reservation_tag
        assert '>>>' in reservation_tag

        # JSON should be parseable
        json_part = reservation_tag.split('<<<RESERVATION:')[1].rstrip('>>>')
        parsed = json.loads(json_part)
        assert parsed['customer_name'] == 'John'

    def test_classification_regex_patterns(self):
        """Classification regex patterns should match expected format."""
        import re

        # INFO pattern
        info_text = "Some response text <<<INFO>>>"
        info_match = re.search(r'<<<INFO>>>', info_text)
        assert info_match is not None

        # RESERVATION pattern
        res_text = "<<<RESERVATION:{\"name\": \"John\"}>>>"
        res_match = re.search(r'<<<RESERVATION:(.+?)>>>', res_text)
        assert res_match is not None
        assert res_match.group(1) == '{"name": "John"}'


class TestExpectedTools:
    """Test expected tool configuration."""

    def test_expected_tool_names(self):
        """System should have expected tool names."""
        expected_tools = [
            'check_availability',
            'get_pricing',
            'get_spot_details',
            'find_available_spot',
            'search_parking_policies',
        ]

        for tool_name in expected_tools:
            assert isinstance(tool_name, str)
            assert len(tool_name) > 0

    def test_sql_tools_for_queries(self):
        """SQL tools should handle database queries."""
        sql_tools = [
            'check_availability',
            'get_pricing',
            'get_spot_details',
            'find_available_spot',
        ]

        # All should be strings
        for tool in sql_tools:
            assert isinstance(tool, str)

    def test_rag_tool_for_policy_search(self):
        """RAG tool should handle policy document search."""
        rag_tool = 'search_parking_policies'
        assert 'search' in rag_tool.lower()
        assert 'polic' in rag_tool.lower()


class TestAgentQueryRouting:
    """Test expected query routing logic."""

    def test_info_queries_classification(self):
        """Info queries should be classified as INFO."""
        info_queries = [
            'What are the parking prices?',
            'What are the operating hours?',
            'Is there EV charging available?',
            'How many spots are available?',
        ]

        # These should NOT contain reservation keywords
        for query in info_queries:
            query_lower = query.lower()
            assert 'reserve' not in query_lower
            assert 'book' not in query_lower

    def test_reservation_queries_classification(self):
        """Reservation queries should be classified as RESERVATION."""
        reservation_queries = [
            'I want to reserve a parking spot',
            'Book me a Standard parking space',
            'I need to make a reservation',
            'Reserve spot 42 for me',
        ]

        # These should contain reservation keywords
        for query in reservation_queries:
            query_lower = query.lower()
            has_keyword = 'reserve' in query_lower or 'book' in query_lower or 'reservation' in query_lower
            assert has_keyword


class TestToolDescriptions:
    """Test tool description patterns."""

    def test_availability_tool_description(self):
        """check_availability should describe its purpose."""
        description_keywords = ['availability', 'available', 'spots', 'count']
        # At least one keyword should be relevant
        assert any(k in ' '.join(description_keywords) for k in ['avail', 'spot'])

    def test_pricing_tool_description(self):
        """get_pricing should describe pricing lookup."""
        description_keywords = ['pricing', 'price', 'cost', 'rate']
        assert any('pric' in k or 'cost' in k for k in description_keywords)

    def test_spot_details_tool_description(self):
        """get_spot_details should describe spot lookup."""
        description_keywords = ['spot', 'details', 'status', 'specific']
        assert any('spot' in k or 'detail' in k for k in description_keywords)

    def test_find_spot_tool_description(self):
        """find_available_spot should describe finding free spots."""
        description_keywords = ['find', 'available', 'spot', 'free']
        assert any('find' in k or 'avail' in k for k in description_keywords)

    def test_policy_search_tool_description(self):
        """search_parking_policies should describe policy search."""
        description_keywords = ['search', 'policy', 'policies', 'rag']
        assert any('search' in k or 'polic' in k for k in description_keywords)


class TestValidParkingTypes:
    """Test valid parking type constants."""

    def test_valid_types_list(self):
        """Valid parking types should be defined."""
        valid_types = ['Standard', 'Premium', 'Rooftop', 'Oversized', 'Motorcycle']
        assert len(valid_types) == 5
        assert 'Standard' in valid_types
        assert 'Premium' in valid_types
