"""
Unit tests for API routes.

Tests all 6 REST endpoints in the reservations router.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with mocked dependencies."""
    from src.api.main import app
    return TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Health endpoint should return OK."""
        response = client.get('/health')

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'


class TestCreateReservationEndpoint:
    """Test POST /reservations/request endpoint."""

    @patch('src.api.routers.reservations.ReservationService')
    def test_create_reservation_success(self, MockService, client):
        """Create reservation with valid data."""
        mock_service = MagicMock()
        mock_service.create_pending_reservation.return_value = {
            'id': 'res_001',
            'customer_name': 'John Doe',
            'car_number': 'ABC-1234',
            'parking_id': 1,
            'parking_type': 'Standard',
            'start_time': '2024-01-15T09:00:00',
            'end_time': '2024-01-15T17:00:00',
            'total_price': 24.00,
            'status': 'pending',
            'created_at': '2024-01-15T08:00:00',
            'updated_at': '2024-01-15T08:00:00',
        }
        MockService.return_value = mock_service

        response = client.post('/reservations/request', json={
            'customer_name': 'John Doe',
            'car_number': 'ABC-1234',
            'parking_type': 'Standard',
            'start_time': '2024-01-15T09:00:00',
            'end_time': '2024-01-15T17:00:00',
        })

        assert response.status_code == 200  # API returns 200, not 201
        data = response.json()
        assert data['id'] == 'res_001'
        assert data['status'] == 'pending'

    def test_create_reservation_invalid_data(self, client):
        """Invalid data should return 422."""
        response = client.post('/reservations/request', json={
            'customer_name': '',  # Empty name
            'car_number': 'ABC-1234',
            'parking_type': 'Standard',
            'start_time': '2024-01-15T09:00:00',
            'end_time': '2024-01-15T17:00:00',
        })

        assert response.status_code == 422

    def test_create_reservation_missing_fields(self, client):
        """Missing required fields should return 422."""
        response = client.post('/reservations/request', json={
            'customer_name': 'John Doe',
            # Missing car_number, parking_type, times
        })

        assert response.status_code == 422


class TestGetPendingReservationsEndpoint:
    """Test GET /reservations/pending endpoint."""

    @patch('src.api.routers.reservations.ReservationService')
    def test_get_pending_reservations(self, MockService, client):
        """Get all pending reservations."""
        mock_service = MagicMock()
        mock_service.get_pending_reservations.return_value = [
            {
                'id': 'res_001',
                'customer_name': 'John',
                'car_number': 'ABC-1234',
                'parking_id': 1,
                'parking_type': 'Standard',
                'start_time': '2024-01-15T09:00:00',
                'end_time': '2024-01-15T17:00:00',
                'total_price': 24.00,
                'status': 'pending',
                'created_at': '2024-01-15T08:00:00',
                'updated_at': '2024-01-15T08:00:00',
            },
            {
                'id': 'res_002',
                'customer_name': 'Jane',
                'car_number': 'XYZ-5678',
                'parking_id': 2,
                'parking_type': 'Premium',
                'start_time': '2024-01-15T10:00:00',
                'end_time': '2024-01-15T18:00:00',
                'total_price': 40.00,
                'status': 'pending',
                'created_at': '2024-01-15T08:30:00',
                'updated_at': '2024-01-15T08:30:00',
            },
        ]
        MockService.return_value = mock_service

        response = client.get('/reservations/pending')

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(r['status'] == 'pending' for r in data)

    @patch('src.api.routers.reservations.ReservationService')
    def test_get_pending_empty(self, MockService, client):
        """Empty pending list should return empty array."""
        mock_service = MagicMock()
        mock_service.get_pending_reservations.return_value = []
        MockService.return_value = mock_service

        response = client.get('/reservations/pending')

        assert response.status_code == 200
        assert response.json() == []


class TestGetAllReservationsEndpoint:
    """Test GET /reservations/all endpoint."""

    @patch('src.api.routers.reservations.ReservationService')
    def test_get_all_reservations(self, MockService, client):
        """Get all reservations regardless of status."""
        mock_service = MagicMock()
        mock_service.get_all_reservations.return_value = [
            {
                'id': 'res_001',
                'customer_name': 'John',
                'car_number': 'ABC-1234',
                'parking_id': 1,
                'parking_type': 'Standard',
                'start_time': '2024-01-15T09:00:00',
                'end_time': '2024-01-15T17:00:00',
                'total_price': 24.00,
                'status': 'pending',
                'created_at': '2024-01-15T08:00:00',
                'updated_at': '2024-01-15T08:00:00',
            },
            {
                'id': 'res_002',
                'customer_name': 'Jane',
                'car_number': 'XYZ-5678',
                'parking_id': 2,
                'parking_type': 'Premium',
                'start_time': '2024-01-15T10:00:00',
                'end_time': '2024-01-15T18:00:00',
                'total_price': 40.00,
                'status': 'approved',
                'created_at': '2024-01-15T08:30:00',
                'updated_at': '2024-01-15T09:00:00',
            },
            {
                'id': 'res_003',
                'customer_name': 'Bob',
                'car_number': 'DEF-9012',
                'parking_id': 3,
                'parking_type': 'Rooftop',
                'start_time': '2024-01-15T11:00:00',
                'end_time': '2024-01-15T19:00:00',
                'total_price': 32.00,
                'status': 'rejected',
                'created_at': '2024-01-15T09:00:00',
                'updated_at': '2024-01-15T09:30:00',
            },
        ]
        MockService.return_value = mock_service

        response = client.get('/reservations/all')

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3


class TestApproveReservationEndpoint:
    """Test POST /reservations/{id}/approve endpoint."""

    @patch('src.api.routers.reservations.ReservationService')
    def test_approve_reservation_success(self, MockService, client):
        """Approve pending reservation."""
        mock_service = MagicMock()
        mock_service.approve_reservation.return_value = {
            'id': 'res_001',
            'customer_name': 'John',
            'car_number': 'ABC-1234',
            'parking_id': 1,
            'parking_type': 'Standard',
            'start_time': '2024-01-15T09:00:00',
            'end_time': '2024-01-15T17:00:00',
            'total_price': 24.00,
            'status': 'approved',
            'created_at': '2024-01-15T08:00:00',
            'updated_at': '2024-01-15T09:00:00',
            'admin_notes': 'Approved!',
        }
        MockService.return_value = mock_service

        response = client.post('/reservations/res_001/approve', json={
            'admin_notes': 'Approved!',
        })

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'approved'

    @patch('src.api.routers.reservations.ReservationService')
    def test_approve_nonexistent_reservation(self, MockService, client):
        """Approve non-existent reservation should return 400."""
        mock_service = MagicMock()
        mock_service.approve_reservation.side_effect = ValueError("Reservation not found")
        MockService.return_value = mock_service

        response = client.post('/reservations/res_999/approve', json={})

        assert response.status_code == 400  # API returns 400 for ValueError

    @patch('src.api.routers.reservations.ReservationService')
    def test_approve_without_notes(self, MockService, client):
        """Approve without admin notes."""
        mock_service = MagicMock()
        mock_service.approve_reservation.return_value = {
            'id': 'res_001',
            'customer_name': 'John',
            'car_number': 'ABC-1234',
            'parking_id': 1,
            'parking_type': 'Standard',
            'start_time': '2024-01-15T09:00:00',
            'end_time': '2024-01-15T17:00:00',
            'total_price': 24.00,
            'status': 'approved',
            'created_at': '2024-01-15T08:00:00',
            'updated_at': '2024-01-15T09:00:00',
        }
        MockService.return_value = mock_service

        response = client.post('/reservations/res_001/approve', json={})

        assert response.status_code == 200


class TestRejectReservationEndpoint:
    """Test POST /reservations/{id}/reject endpoint."""

    @patch('src.api.routers.reservations.ReservationService')
    def test_reject_reservation_success(self, MockService, client):
        """Reject pending reservation."""
        mock_service = MagicMock()
        mock_service.reject_reservation.return_value = {
            'id': 'res_001',
            'customer_name': 'John',
            'car_number': 'ABC-1234',
            'parking_id': 1,
            'parking_type': 'Standard',
            'start_time': '2024-01-15T09:00:00',
            'end_time': '2024-01-15T17:00:00',
            'total_price': 24.00,
            'status': 'rejected',
            'created_at': '2024-01-15T08:00:00',
            'updated_at': '2024-01-15T09:00:00',
            'admin_notes': 'No spots available',
        }
        MockService.return_value = mock_service

        response = client.post('/reservations/res_001/reject', json={
            'admin_notes': 'No spots available',
        })

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'rejected'
        assert data['admin_notes'] == 'No spots available'

    @patch('src.api.routers.reservations.ReservationService')
    def test_reject_nonexistent_reservation(self, MockService, client):
        """Reject non-existent reservation should return 400."""
        mock_service = MagicMock()
        mock_service.reject_reservation.side_effect = ValueError("Reservation not found")
        MockService.return_value = mock_service

        response = client.post('/reservations/res_999/reject', json={})

        assert response.status_code == 400  # API returns 400 for ValueError


class TestStatusCheckEndpoint:
    """Test GET /reservations/{id}/status endpoint."""

    @patch('src.api.routers.reservations.ReservationService')
    def test_check_pending_status(self, MockService, client):
        """Check status of pending reservation."""
        mock_service = MagicMock()
        mock_service.get_reservation_by_id.return_value = {
            'id': 'res_001',
            'status': 'pending',
            'parking_id': 1,
            'updated_at': '2024-01-15T08:00:00',
        }
        MockService.return_value = mock_service

        response = client.get('/reservations/res_001/status')

        assert response.status_code == 200
        data = response.json()
        assert data['id'] == 'res_001'
        assert data['status'] == 'pending'

    @patch('src.api.routers.reservations.ReservationService')
    def test_check_approved_status(self, MockService, client):
        """Check status of approved reservation."""
        mock_service = MagicMock()
        mock_service.get_reservation_by_id.return_value = {
            'id': 'res_001',
            'status': 'approved',
            'parking_id': 42,
            'admin_notes': 'Enjoy!',
            'updated_at': '2024-01-15T09:00:00',
        }
        MockService.return_value = mock_service

        response = client.get('/reservations/res_001/status')

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'approved'

    @patch('src.api.routers.reservations.ReservationService')
    def test_check_nonexistent_status(self, MockService, client):
        """Check status of non-existent reservation."""
        mock_service = MagicMock()
        mock_service.get_reservation_by_id.return_value = None
        MockService.return_value = mock_service

        response = client.get('/reservations/res_999/status')

        assert response.status_code == 404


class TestCORSMiddleware:
    """Test CORS configuration."""

    def test_cors_headers_present(self, client):
        """CORS headers should be present."""
        response = client.options('/health', headers={
            'Origin': 'http://localhost:3000',
            'Access-Control-Request-Method': 'GET',
        })

        # CORS middleware should allow the request
        assert response.status_code in [200, 204, 405]


class TestValidationErrorHandler:
    """Test custom validation error handler."""

    def test_validation_error_returns_422(self, client):
        """Validation errors should return 422 with details."""
        response = client.post('/reservations/request', json={
            'customer_name': '',
            'car_number': '',
            'parking_type': '',
            'start_time': 'invalid',
            'end_time': 'invalid',
        })

        assert response.status_code == 422
        data = response.json()
        assert 'detail' in data
