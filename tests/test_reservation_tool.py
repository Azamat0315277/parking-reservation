"""
Unit tests for parking reservation tool.

Tests validation logic and database reservation operations.
"""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch


class TestReservationRequestValidation:
    """Test input validation for reserve_parking_space."""

    @patch('src.tools.parking_reservation_tool.engine')
    def test_valid_reservation_request(self, mock_engine):
        """Valid request should process successfully."""
        from src.tools.parking_reservation_tool import reserve_parking_space

        # Mock database responses
        mock_conn = MagicMock()

        # Mock availability check - returns tuple (parking_id, parking_type, space_availability)
        mock_avail_result = MagicMock()
        mock_avail_result.fetchone.return_value = (1, 'Standard', True)

        # Mock update result
        mock_update_result = MagicMock()
        mock_update_result.rowcount = 1

        mock_conn.execute.side_effect = [mock_avail_result, mock_update_result]
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        start_time = (datetime.now() + timedelta(hours=1)).isoformat()
        end_time = (datetime.now() + timedelta(hours=3)).isoformat()

        request = json.dumps({
            'parking_id': 1,
            'parking_type': 'Standard',
            'start_time': start_time,
            'end_time': end_time,
        })

        result = reserve_parking_space.invoke(request)

        assert 'confirmed' in result.lower() or 'reserved' in result.lower()

    @patch('src.tools.parking_reservation_tool.engine')
    def test_invalid_parking_id_zero(self, mock_engine):
        """Parking ID must be positive."""
        from src.tools.parking_reservation_tool import reserve_parking_space

        request = json.dumps({
            'parking_id': 0,
            'parking_type': 'Standard',
            'start_time': datetime.now().isoformat(),
            'end_time': (datetime.now() + timedelta(hours=1)).isoformat(),
        })

        result = reserve_parking_space.invoke(request)

        assert 'invalid' in result.lower()

    @patch('src.tools.parking_reservation_tool.engine')
    def test_invalid_parking_id_negative(self, mock_engine):
        """Negative parking ID should fail."""
        from src.tools.parking_reservation_tool import reserve_parking_space

        request = json.dumps({
            'parking_id': -5,
            'parking_type': 'Standard',
            'start_time': datetime.now().isoformat(),
            'end_time': (datetime.now() + timedelta(hours=1)).isoformat(),
        })

        result = reserve_parking_space.invoke(request)

        assert 'invalid' in result.lower()

    @patch('src.tools.parking_reservation_tool.engine')
    def test_invalid_parking_type(self, mock_engine):
        """Invalid parking type should fail."""
        from src.tools.parking_reservation_tool import reserve_parking_space

        request = json.dumps({
            'parking_id': 1,
            'parking_type': 'invalid_type',
            'start_time': datetime.now().isoformat(),
            'end_time': (datetime.now() + timedelta(hours=1)).isoformat(),
        })

        result = reserve_parking_space.invoke(request)

        assert 'invalid' in result.lower() or 'type' in result.lower()

    @patch('src.tools.parking_reservation_tool.engine')
    def test_end_time_before_start_time(self, mock_engine):
        """End time must be after start time."""
        from src.tools.parking_reservation_tool import reserve_parking_space

        start_time = (datetime.now() + timedelta(hours=3)).isoformat()
        end_time = (datetime.now() + timedelta(hours=1)).isoformat()

        request = json.dumps({
            'parking_id': 1,
            'parking_type': 'Standard',
            'start_time': start_time,
            'end_time': end_time,
        })

        result = reserve_parking_space.invoke(request)

        assert 'time' in result.lower()

    @patch('src.tools.parking_reservation_tool.engine')
    def test_invalid_timestamp_format(self, mock_engine):
        """Invalid timestamp format should fail."""
        from src.tools.parking_reservation_tool import reserve_parking_space

        request = json.dumps({
            'parking_id': 1,
            'parking_type': 'Standard',
            'start_time': 'not-a-timestamp',
            'end_time': 'also-not-valid',
        })

        result = reserve_parking_space.invoke(request)

        assert 'invalid' in result.lower()

    @patch('src.tools.parking_reservation_tool.engine')
    def test_missing_required_fields(self, mock_engine):
        """Missing required fields should fail."""
        from src.tools.parking_reservation_tool import reserve_parking_space

        # Missing parking_type
        request = json.dumps({
            'parking_id': 1,
            'start_time': datetime.now().isoformat(),
            'end_time': (datetime.now() + timedelta(hours=1)).isoformat(),
        })

        result = reserve_parking_space.invoke(request)

        assert 'invalid' in result.lower() or 'type' in result.lower()

    @patch('src.tools.parking_reservation_tool.engine')
    def test_invalid_json_input(self, mock_engine):
        """Invalid JSON should fail gracefully."""
        from src.tools.parking_reservation_tool import reserve_parking_space

        result = reserve_parking_space.invoke("not valid json {{{")

        assert 'invalid' in result.lower()


class TestSpotAvailabilityCheck:
    """Test spot availability validation."""

    @patch('src.tools.parking_reservation_tool.engine')
    def test_spot_not_available(self, mock_engine):
        """Unavailable spot should be rejected."""
        from src.tools.parking_reservation_tool import reserve_parking_space

        mock_conn = MagicMock()
        mock_result = MagicMock()
        # Tuple: (parking_id, parking_type, space_availability)
        mock_result.fetchone.return_value = (1, 'Standard', False)

        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        request = json.dumps({
            'parking_id': 1,
            'parking_type': 'Standard',
            'start_time': (datetime.now() + timedelta(hours=1)).isoformat(),
            'end_time': (datetime.now() + timedelta(hours=3)).isoformat(),
        })

        result = reserve_parking_space.invoke(request)

        assert 'not available' in result.lower() or 'reserved' in result.lower()

    @patch('src.tools.parking_reservation_tool.engine')
    def test_spot_not_found(self, mock_engine):
        """Non-existent spot should fail."""
        from src.tools.parking_reservation_tool import reserve_parking_space

        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None

        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        request = json.dumps({
            'parking_id': 9999,
            'parking_type': 'Standard',
            'start_time': (datetime.now() + timedelta(hours=1)).isoformat(),
            'end_time': (datetime.now() + timedelta(hours=3)).isoformat(),
        })

        result = reserve_parking_space.invoke(request)

        assert 'does not exist' in result.lower() or 'not found' in result.lower()

    @patch('src.tools.parking_reservation_tool.engine')
    def test_type_mismatch(self, mock_engine):
        """Spot type must match requested type."""
        from src.tools.parking_reservation_tool import reserve_parking_space

        mock_conn = MagicMock()
        mock_result = MagicMock()
        # Tuple: (parking_id, parking_type, space_availability)
        mock_result.fetchone.return_value = (1, 'Premium', True)

        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        request = json.dumps({
            'parking_id': 1,
            'parking_type': 'Standard',  # Requesting Standard, but spot is Premium
            'start_time': (datetime.now() + timedelta(hours=1)).isoformat(),
            'end_time': (datetime.now() + timedelta(hours=3)).isoformat(),
        })

        result = reserve_parking_space.invoke(request)

        assert 'not of type' in result.lower() or 'type' in result.lower()


class TestValidParkingTypes:
    """Test valid parking type constants."""

    def test_valid_types_defined(self):
        """Valid parking types should be defined."""
        from src.tools.parking_reservation_tool import VALID_TYPES

        expected = {'Standard', 'Premium', 'Rooftop', 'Oversized', 'Motorcycle'}
        assert VALID_TYPES == expected

    @patch('src.tools.parking_reservation_tool.engine')
    def test_all_valid_types_accepted(self, mock_engine):
        """All valid parking types should be accepted."""
        from src.tools.parking_reservation_tool import reserve_parking_space, VALID_TYPES

        for parking_type in VALID_TYPES:
            mock_conn = MagicMock()
            mock_result = MagicMock()
            # Tuple: (parking_id, parking_type, space_availability)
            mock_result.fetchone.return_value = (1, parking_type, True)

            mock_update = MagicMock()
            mock_update.rowcount = 1

            mock_conn.execute.side_effect = [mock_result, mock_update]
            mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

            request = json.dumps({
                'parking_id': 1,
                'parking_type': parking_type,
                'start_time': (datetime.now() + timedelta(hours=1)).isoformat(),
                'end_time': (datetime.now() + timedelta(hours=3)).isoformat(),
            })

            result = reserve_parking_space.invoke(request)

            # Should not contain type validation error
            assert 'invalid' not in result.lower() or 'type' not in result.lower()


class TestDatabaseOperations:
    """Test database update operations."""

    @patch('src.tools.parking_reservation_tool.engine')
    def test_successful_update(self, mock_engine):
        """Successful reservation should update database."""
        from src.tools.parking_reservation_tool import reserve_parking_space

        mock_conn = MagicMock()

        # Availability check - Tuple: (parking_id, parking_type, space_availability)
        mock_avail = MagicMock()
        mock_avail.fetchone.return_value = (1, 'Standard', True)

        # Update result
        mock_update = MagicMock()
        mock_update.rowcount = 1

        mock_conn.execute.side_effect = [mock_avail, mock_update]
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        request = json.dumps({
            'parking_id': 1,
            'parking_type': 'Standard',
            'start_time': (datetime.now() + timedelta(hours=1)).isoformat(),
            'end_time': (datetime.now() + timedelta(hours=3)).isoformat(),
        })

        result = reserve_parking_space.invoke(request)

        # Should indicate success
        assert 'confirmed' in result.lower()
        # Should have called execute twice (check + update)
        assert mock_conn.execute.call_count >= 2

    @patch('src.tools.parking_reservation_tool.engine')
    def test_update_fails(self, mock_engine):
        """Handle database update failure."""
        from src.tools.parking_reservation_tool import reserve_parking_space

        mock_conn = MagicMock()

        # Availability check succeeds - Tuple: (parking_id, parking_type, space_availability)
        mock_avail = MagicMock()
        mock_avail.fetchone.return_value = (1, 'Standard', True)

        # Update fails (no rows affected)
        mock_update = MagicMock()
        mock_update.rowcount = 0

        mock_conn.execute.side_effect = [mock_avail, mock_update]
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        request = json.dumps({
            'parking_id': 1,
            'parking_type': 'Standard',
            'start_time': (datetime.now() + timedelta(hours=1)).isoformat(),
            'end_time': (datetime.now() + timedelta(hours=3)).isoformat(),
        })

        result = reserve_parking_space.invoke(request)

        # Should indicate failure (not available or already reserved)
        assert 'not available' in result.lower() or 'reserved' in result.lower()


class TestParameterizedQueries:
    """Test SQL injection prevention."""

    @patch('src.tools.parking_reservation_tool.engine')
    def test_sql_injection_in_parking_type(self, mock_engine):
        """SQL injection attempt in parking_type should be safe."""
        from src.tools.parking_reservation_tool import reserve_parking_space

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        request = json.dumps({
            'parking_id': 1,
            'parking_type': "'; DROP TABLE parking_lots; --",
            'start_time': (datetime.now() + timedelta(hours=1)).isoformat(),
            'end_time': (datetime.now() + timedelta(hours=3)).isoformat(),
        })

        result = reserve_parking_space.invoke(request)

        # Should fail validation (invalid type), not execute SQL
        assert 'invalid' in result.lower()
