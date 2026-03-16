"""
Unit tests for SQL reader tools.

Tests the 4 read-only SQL tools:
- check_availability
- get_pricing
- get_spot_details
- find_available_spot
"""

import pytest
from unittest.mock import MagicMock, patch


class TestCheckAvailability:
    """Test check_availability tool."""

    @patch('src.tools.sql_reader_tool.engine')
    def test_check_all_availability(self, mock_engine):
        """Check availability for all parking types."""
        from src.tools.sql_reader_tool import check_availability

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [
            ('Standard', 10),
            ('Premium', 5),
        ]
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        result = check_availability.invoke({})

        assert 'Standard' in result
        assert 'available' in result.lower()

    @patch('src.tools.sql_reader_tool.engine')
    def test_check_availability_by_type(self, mock_engine):
        """Check availability for specific parking type."""
        from src.tools.sql_reader_tool import check_availability

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [
            ('Premium', 5),
        ]
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        result = check_availability.invoke({'parking_type': 'Premium'})

        assert 'Premium' in result

    @patch('src.tools.sql_reader_tool.engine')
    def test_check_availability_empty_result(self, mock_engine):
        """Handle no available spots."""
        from src.tools.sql_reader_tool import check_availability

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        result = check_availability.invoke({'parking_type': 'nonexistent'})

        assert 'no available' in result.lower()


class TestGetPricing:
    """Test get_pricing tool."""

    @patch('src.tools.sql_reader_tool.engine')
    def test_get_all_pricing(self, mock_engine):
        """Get pricing for all parking types."""
        from src.tools.sql_reader_tool import get_pricing

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [
            ('Premium', 5.0),
            ('Standard', 3.0),
        ]
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        result = get_pricing.invoke({})

        assert '$' in result
        assert 'Premium' in result

    @patch('src.tools.sql_reader_tool.engine')
    def test_get_pricing_by_type(self, mock_engine):
        """Get pricing for specific type."""
        from src.tools.sql_reader_tool import get_pricing

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [
            ('Standard', 3.0),
        ]
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        result = get_pricing.invoke({'parking_type': 'Standard'})

        assert 'Standard' in result

    @patch('src.tools.sql_reader_tool.engine')
    def test_get_pricing_empty(self, mock_engine):
        """Handle no pricing found."""
        from src.tools.sql_reader_tool import get_pricing

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        result = get_pricing.invoke({})

        assert 'no pricing' in result.lower()


class TestGetSpotDetails:
    """Test get_spot_details tool."""

    @patch('src.tools.sql_reader_tool.engine')
    def test_get_existing_spot(self, mock_engine):
        """Get details for existing spot."""
        from src.tools.sql_reader_tool import get_spot_details

        mock_conn = MagicMock()
        # Row: parking_id, parking_type, space_availability, reservation_start, reservation_end, price
        mock_conn.execute.return_value.fetchone.return_value = (42, 'Premium', True, None, None, 5.0)
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        result = get_spot_details.invoke({'parking_id': 42})

        assert '42' in result
        assert 'Premium' in result
        assert 'Available' in result

    @patch('src.tools.sql_reader_tool.engine')
    def test_get_reserved_spot(self, mock_engine):
        """Get details for reserved spot."""
        from src.tools.sql_reader_tool import get_spot_details

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = (
            10, 'Standard', False, '2024-01-15 09:00', '2024-01-15 17:00', 3.0
        )
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        result = get_spot_details.invoke({'parking_id': 10})

        assert 'Reserved' in result
        assert '09:00' in result

    @patch('src.tools.sql_reader_tool.engine')
    def test_get_nonexistent_spot(self, mock_engine):
        """Handle non-existent spot ID."""
        from src.tools.sql_reader_tool import get_spot_details

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        result = get_spot_details.invoke({'parking_id': 9999})

        assert 'does not exist' in result


class TestFindAvailableSpot:
    """Test find_available_spot tool."""

    @patch('src.tools.sql_reader_tool.engine')
    def test_find_available_spot(self, mock_engine):
        """Find available parking spot."""
        from src.tools.sql_reader_tool import find_available_spot

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = (15,)
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        result = find_available_spot.invoke({'parking_type': 'Standard'})

        assert '15' in result

    @patch('src.tools.sql_reader_tool.engine')
    def test_find_no_available_spot(self, mock_engine):
        """Handle no available spots."""
        from src.tools.sql_reader_tool import find_available_spot

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        result = find_available_spot.invoke({'parking_type': 'Premium'})

        assert 'no available' in result.lower()


class TestToolDecorators:
    """Test that tools are properly decorated."""

    def test_check_availability_is_tool(self):
        """check_availability should be a LangChain tool."""
        from src.tools.sql_reader_tool import check_availability
        assert hasattr(check_availability, 'invoke')
        assert hasattr(check_availability, 'name')

    def test_get_pricing_is_tool(self):
        """get_pricing should be a LangChain tool."""
        from src.tools.sql_reader_tool import get_pricing
        assert hasattr(get_pricing, 'invoke')

    def test_get_spot_details_is_tool(self):
        """get_spot_details should be a LangChain tool."""
        from src.tools.sql_reader_tool import get_spot_details
        assert hasattr(get_spot_details, 'invoke')

    def test_find_available_spot_is_tool(self):
        """find_available_spot should be a LangChain tool."""
        from src.tools.sql_reader_tool import find_available_spot
        assert hasattr(find_available_spot, 'invoke')
