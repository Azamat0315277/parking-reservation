"""
Unit tests for ReservationService.

Tests core business logic for reservation management including
file I/O, status transitions, and database operations.
"""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, mock_open

from src.api.services.reservation_service import ReservationService


class TestLoadPending:
    """Test _load_pending function."""

    def test_load_existing_file(self, tmp_path):
        """Load reservations from existing file."""
        from src.api.services.reservation_service import _load_pending

        test_data = [
            {'id': 'res_001', 'status': 'pending'},
        ]

        # Create a real temp file
        test_file = tmp_path / 'pending.json'
        test_file.write_text(json.dumps(test_data))

        with patch('src.api.services.reservation_service.PENDING_FILE', test_file):
            data = _load_pending()

        assert len(data) == 1
        assert data[0]['id'] == 'res_001'

    def test_load_nonexistent_file(self, tmp_path):
        """Return empty list for nonexistent file."""
        from src.api.services.reservation_service import _load_pending

        # Point to non-existent file
        test_file = tmp_path / 'nonexistent.json'

        with patch('src.api.services.reservation_service.PENDING_FILE', test_file):
            data = _load_pending()

        assert data == []


class TestSavePending:
    """Test _save_pending function."""

    def test_save_creates_parent_directory(self, tmp_path):
        """Parent directory should be created if needed."""
        from src.api.services.reservation_service import _save_pending

        test_file = tmp_path / "subdir" / "pending.json"

        with patch('src.api.services.reservation_service.PENDING_FILE', test_file):
            _save_pending([{'id': 'test'}])

        assert test_file.exists()
        data = json.loads(test_file.read_text())
        assert len(data) == 1


class TestReservationServiceCreate:
    """Test create_pending_reservation method."""

    @pytest.fixture
    def service(self):
        return ReservationService()

    @patch('src.api.services.reservation_service.find_available_spot')
    @patch('src.api.services.reservation_service._save_pending')
    @patch('src.api.services.reservation_service._load_pending')
    @patch('src.api.services.reservation_service.FileLock')
    def test_create_with_parking_id(self, mock_lock, mock_load, mock_save, mock_find, service):
        """Create reservation with specified parking_id."""
        mock_load.return_value = []
        mock_lock.return_value.__enter__ = MagicMock()
        mock_lock.return_value.__exit__ = MagicMock()

        result = service.create_pending_reservation(
            parking_id=42,
            parking_type='Standard',
            start_time='2024-01-15T09:00:00',
            end_time='2024-01-15T17:00:00',
            customer_name='John Doe',
            car_number='ABC-1234',
        )

        assert result['parking_id'] == 42
        assert result['status'] == 'pending'
        assert 'id' in result
        mock_find.invoke.assert_not_called()  # Should not call find when ID provided

    @patch('src.api.services.reservation_service.find_available_spot')
    @patch('src.api.services.reservation_service._save_pending')
    @patch('src.api.services.reservation_service._load_pending')
    @patch('src.api.services.reservation_service.FileLock')
    def test_create_auto_find_spot(self, mock_lock, mock_load, mock_save, mock_find, service):
        """Auto-find spot when parking_id not provided."""
        mock_load.return_value = []
        mock_lock.return_value.__enter__ = MagicMock()
        mock_lock.return_value.__exit__ = MagicMock()
        mock_find.invoke.return_value = 'Spot 15 (Standard) is available'

        result = service.create_pending_reservation(
            parking_id=None,
            parking_type='Standard',
            start_time='2024-01-15T09:00:00',
            end_time='2024-01-15T17:00:00',
            customer_name='Jane Smith',
            car_number='XYZ-5678',
        )

        assert result['parking_id'] == 15
        mock_find.invoke.assert_called_once_with('Standard')

    @patch('src.api.services.reservation_service.find_available_spot')
    @patch('src.api.services.reservation_service.FileLock')
    def test_create_no_spot_available(self, mock_lock, mock_find, service):
        """Raise error when no spot is available."""
        mock_lock.return_value.__enter__ = MagicMock()
        mock_lock.return_value.__exit__ = MagicMock()
        mock_find.invoke.return_value = 'No spots available'

        with pytest.raises(ValueError, match='(No available|Could not find)'):
            service.create_pending_reservation(
                parking_id=None,
                parking_type='Premium',
                start_time='2024-01-15T09:00:00',
                end_time='2024-01-15T17:00:00',
                customer_name='Jane Smith',
                car_number='XYZ-5678',
            )


class TestReservationServiceGetters:
    """Test reservation retrieval methods."""

    @pytest.fixture
    def service(self):
        return ReservationService()

    @patch('src.api.services.reservation_service._load_pending')
    @patch('src.api.services.reservation_service.FileLock')
    def test_get_pending_reservations(self, mock_lock, mock_load, service):
        """Get only pending reservations."""
        mock_lock.return_value.__enter__ = MagicMock()
        mock_lock.return_value.__exit__ = MagicMock()
        mock_load.return_value = [
            {'id': 'res_001', 'status': 'pending'},
            {'id': 'res_002', 'status': 'approved'},
            {'id': 'res_003', 'status': 'pending'},
        ]

        pending = service.get_pending_reservations()

        assert len(pending) == 2
        assert all(r['status'] == 'pending' for r in pending)

    @patch('src.api.services.reservation_service._load_pending')
    @patch('src.api.services.reservation_service.FileLock')
    def test_get_all_reservations(self, mock_lock, mock_load, service):
        """Get all reservations regardless of status."""
        mock_lock.return_value.__enter__ = MagicMock()
        mock_lock.return_value.__exit__ = MagicMock()
        mock_load.return_value = [
            {'id': 'res_001', 'status': 'pending'},
            {'id': 'res_002', 'status': 'approved'},
        ]

        all_reservations = service.get_all_reservations()

        assert len(all_reservations) == 2

    @patch('src.api.services.reservation_service._load_pending')
    @patch('src.api.services.reservation_service.FileLock')
    def test_get_reservation_by_id_found(self, mock_lock, mock_load, service):
        """Get specific reservation by ID."""
        mock_lock.return_value.__enter__ = MagicMock()
        mock_lock.return_value.__exit__ = MagicMock()
        mock_load.return_value = [
            {'id': 'res_001', 'customer_name': 'John'},
            {'id': 'res_002', 'customer_name': 'Jane'},
        ]

        reservation = service.get_reservation_by_id('res_002')

        assert reservation is not None
        assert reservation['customer_name'] == 'Jane'

    @patch('src.api.services.reservation_service._load_pending')
    @patch('src.api.services.reservation_service.FileLock')
    def test_get_reservation_by_id_not_found(self, mock_lock, mock_load, service):
        """Return None for non-existent ID."""
        mock_lock.return_value.__enter__ = MagicMock()
        mock_lock.return_value.__exit__ = MagicMock()
        mock_load.return_value = []

        reservation = service.get_reservation_by_id('res_999')

        assert reservation is None


class TestReservationServiceApprove:
    """Test approve_reservation method."""

    @pytest.fixture
    def service(self):
        return ReservationService()

    @patch('src.api.services.reservation_service.reserve_parking_space')
    @patch('src.api.services.reservation_service._save_pending')
    @patch('src.api.services.reservation_service._load_pending')
    @patch('src.api.services.reservation_service.FileLock')
    def test_approve_pending_reservation(self, mock_lock, mock_load, mock_save, mock_reserve, service):
        """Approve a pending reservation."""
        mock_lock.return_value.__enter__ = MagicMock()
        mock_lock.return_value.__exit__ = MagicMock()
        mock_load.return_value = [
            {
                'id': 'res_001',
                'status': 'pending',
                'customer_name': 'John Doe',
                'car_number': 'ABC-1234',
                'parking_id': 1,
                'parking_type': 'Standard',
                'start_time': '2024-01-15T09:00:00',
                'end_time': '2024-01-15T17:00:00',
            }
        ]
        mock_reserve.invoke.return_value = 'Reservation confirmed'

        with patch.object(service, '_append_to_approved_file'):
            result = service.approve_reservation('res_001', admin_notes='Approved!')

        assert result['status'] == 'approved'
        assert result['admin_notes'] == 'Approved!'

    @patch('src.api.services.reservation_service._load_pending')
    @patch('src.api.services.reservation_service.FileLock')
    def test_approve_nonexistent_reservation(self, mock_lock, mock_load, service):
        """Raise error for non-existent reservation."""
        # Set up FileLock as context manager
        mock_lock_instance = MagicMock()
        mock_lock.return_value = mock_lock_instance
        mock_load.return_value = []

        with pytest.raises(ValueError, match='not found'):
            service.approve_reservation('res_999')

    @patch('src.api.services.reservation_service._load_pending')
    @patch('src.api.services.reservation_service.FileLock')
    def test_approve_already_processed(self, mock_lock, mock_load, service):
        """Raise error for already processed reservation."""
        # Set up FileLock as context manager
        mock_lock_instance = MagicMock()
        mock_lock.return_value = mock_lock_instance
        mock_load.return_value = [
            {'id': 'res_001', 'status': 'approved'}
        ]

        with pytest.raises(ValueError, match='already processed'):
            service.approve_reservation('res_001')


class TestReservationServiceReject:
    """Test reject_reservation method."""

    @pytest.fixture
    def service(self):
        return ReservationService()

    @patch('src.api.services.reservation_service._save_pending')
    @patch('src.api.services.reservation_service._load_pending')
    @patch('src.api.services.reservation_service.FileLock')
    def test_reject_pending_reservation(self, mock_lock, mock_load, mock_save, service):
        """Reject a pending reservation."""
        mock_lock.return_value.__enter__ = MagicMock()
        mock_lock.return_value.__exit__ = MagicMock()
        mock_load.return_value = [
            {'id': 'res_001', 'status': 'pending', 'customer_name': 'John'}
        ]

        result = service.reject_reservation('res_001', admin_notes='No spots')

        assert result['status'] == 'rejected'
        assert result['admin_notes'] == 'No spots'

    @patch('src.api.services.reservation_service._load_pending')
    @patch('src.api.services.reservation_service.FileLock')
    def test_reject_nonexistent_reservation(self, mock_lock, mock_load, service):
        """Raise error for non-existent reservation."""
        # Set up FileLock as context manager
        mock_lock_instance = MagicMock()
        mock_lock.return_value = mock_lock_instance
        mock_load.return_value = []

        with pytest.raises(ValueError, match='not found'):
            service.reject_reservation('res_999')

    @patch('src.api.services.reservation_service._load_pending')
    @patch('src.api.services.reservation_service.FileLock')
    def test_reject_already_approved(self, mock_lock, mock_load, service):
        """Raise error for already approved reservation."""
        # Set up FileLock as context manager
        mock_lock_instance = MagicMock()
        mock_lock.return_value = mock_lock_instance
        mock_load.return_value = [
            {'id': 'res_001', 'status': 'approved'}
        ]

        with pytest.raises(ValueError, match='already processed'):
            service.reject_reservation('res_001')


class TestAppendToApprovedFile:
    """Test _append_to_approved_file method."""

    @pytest.fixture
    def service(self):
        return ReservationService()

    def test_append_formats_correctly(self, service, tmp_path):
        """Approved reservation should be formatted correctly."""
        reservation = {
            'customer_name': 'John Doe',
            'car_number': 'ABC-1234',
            'parking_id': 42,
            'parking_type': 'Premium',
            'start_time': '2024-01-15T09:00:00',
            'end_time': '2024-01-15T17:00:00',
            'updated_at': '2024-01-15T08:30:00',
        }

        approved_file = tmp_path / "approved.txt"
        with patch('src.api.services.reservation_service.APPROVED_FILE', approved_file):
            service._append_to_approved_file(reservation)

        content = approved_file.read_text()
        assert 'John Doe' in content
        assert 'ABC-1234' in content
        assert '42' in content
        assert 'Premium' in content
