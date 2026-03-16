"""
Unit tests for API Pydantic models.

Tests validation rules for request/response schemas.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.api.models.schemas import (
    ReservationStatus,
    ReservationRequest,
    ReservationResponse,
    ApprovalRequest,
    StatusCheckResponse,
)


class TestReservationStatus:
    """Test ReservationStatus enum."""

    def test_valid_statuses(self):
        """All expected statuses should exist."""
        assert ReservationStatus.PENDING.value == 'pending'
        assert ReservationStatus.APPROVED.value == 'approved'
        assert ReservationStatus.REJECTED.value == 'rejected'

    def test_status_count(self):
        """Should have exactly 3 statuses."""
        assert len(ReservationStatus) == 3


class TestReservationRequest:
    """Test ReservationRequest model validation."""

    def test_valid_request_minimal(self):
        """Valid request with minimal required fields."""
        request = ReservationRequest(
            customer_name='John Doe',
            car_number='ABC-1234',
            parking_type='Standard',
            start_time='2024-01-15T09:00:00',
            end_time='2024-01-15T17:00:00',
        )
        assert request.customer_name == 'John Doe'
        assert request.parking_id is None

    def test_valid_request_with_parking_id(self):
        """Valid request with optional parking_id."""
        request = ReservationRequest(
            customer_name='Jane Smith',
            car_number='XYZ-5678',
            parking_type='Premium',
            start_time='2024-01-15T09:00:00',
            end_time='2024-01-15T17:00:00',
            parking_id=42,
        )
        assert request.parking_id == 42

    def test_invalid_customer_name_empty(self):
        """Empty customer name should fail."""
        with pytest.raises(ValidationError) as exc_info:
            ReservationRequest(
                customer_name='',
                car_number='ABC-1234',
                parking_type='Standard',
                start_time='2024-01-15T09:00:00',
                end_time='2024-01-15T17:00:00',
            )
        assert 'customer_name' in str(exc_info.value)

    def test_invalid_car_number_empty(self):
        """Empty car number should fail."""
        with pytest.raises(ValidationError) as exc_info:
            ReservationRequest(
                customer_name='John Doe',
                car_number='',
                parking_type='Standard',
                start_time='2024-01-15T09:00:00',
                end_time='2024-01-15T17:00:00',
            )
        assert 'car_number' in str(exc_info.value)

    def test_invalid_parking_id_zero(self):
        """Parking ID must be > 0."""
        with pytest.raises(ValidationError) as exc_info:
            ReservationRequest(
                customer_name='John Doe',
                car_number='ABC-1234',
                parking_type='Standard',
                start_time='2024-01-15T09:00:00',
                end_time='2024-01-15T17:00:00',
                parking_id=0,
            )
        assert 'parking_id' in str(exc_info.value)

    def test_invalid_parking_id_negative(self):
        """Negative parking ID should fail."""
        with pytest.raises(ValidationError) as exc_info:
            ReservationRequest(
                customer_name='John Doe',
                car_number='ABC-1234',
                parking_type='Standard',
                start_time='2024-01-15T09:00:00',
                end_time='2024-01-15T17:00:00',
                parking_id=-1,
            )
        assert 'parking_id' in str(exc_info.value)

    def test_invalid_parking_type(self):
        """Invalid parking type should fail validation."""
        with pytest.raises(ValidationError):
            ReservationRequest(
                customer_name='John Doe',
                car_number='ABC-1234',
                parking_type='invalid_type',
                start_time='2024-01-15T09:00:00',
                end_time='2024-01-15T17:00:00',
            )

    def test_valid_parking_types(self):
        """All valid parking types should be accepted."""
        valid_types = ['Standard', 'Premium', 'Rooftop', 'Oversized', 'Motorcycle']
        for parking_type in valid_types:
            request = ReservationRequest(
                customer_name='John Doe',
                car_number='ABC-1234',
                parking_type=parking_type,
                start_time='2024-01-15T09:00:00',
                end_time='2024-01-15T17:00:00',
            )
            assert request.parking_type == parking_type

    def test_serialization(self):
        """Test model serialization to dict."""
        request = ReservationRequest(
            customer_name='John Doe',
            car_number='ABC-1234',
            parking_type='Standard',
            start_time='2024-01-15T09:00:00',
            end_time='2024-01-15T17:00:00',
        )
        data = request.model_dump()
        assert data['customer_name'] == 'John Doe'
        assert data['car_number'] == 'ABC-1234'


class TestReservationResponse:
    """Test ReservationResponse model."""

    def test_valid_response(self):
        """Valid response with all fields."""
        response = ReservationResponse(
            id='res_001',
            customer_name='John Doe',
            car_number='ABC-1234',
            parking_id=1,
            parking_type='Standard',
            start_time='2024-01-15T09:00:00',
            end_time='2024-01-15T17:00:00',
            total_price=24.0,
            status=ReservationStatus.PENDING,
            created_at='2024-01-15T08:00:00',
            updated_at='2024-01-15T08:00:00',
        )
        assert response.id == 'res_001'
        assert response.status == ReservationStatus.PENDING
        assert response.admin_notes is None

    def test_response_with_admin_notes(self):
        """Response with optional admin notes."""
        response = ReservationResponse(
            id='res_001',
            customer_name='John Doe',
            car_number='ABC-1234',
            parking_id=1,
            parking_type='Standard',
            start_time='2024-01-15T09:00:00',
            end_time='2024-01-15T17:00:00',
            total_price=24.0,
            status=ReservationStatus.REJECTED,
            created_at='2024-01-15T08:00:00',
            updated_at='2024-01-15T08:30:00',
            admin_notes='Spot unavailable',
        )
        assert response.admin_notes == 'Spot unavailable'

    def test_response_serialization_with_enum(self):
        """Enum should serialize properly."""
        response = ReservationResponse(
            id='res_001',
            customer_name='John Doe',
            car_number='ABC-1234',
            parking_id=1,
            parking_type='Standard',
            start_time='2024-01-15T09:00:00',
            end_time='2024-01-15T17:00:00',
            total_price=None,
            status=ReservationStatus.APPROVED,
            created_at='2024-01-15T08:00:00',
            updated_at='2024-01-15T08:30:00',
        )
        data = response.model_dump()
        assert data['status'] == 'approved'


class TestApprovalRequest:
    """Test ApprovalRequest model."""

    def test_approval_with_notes(self):
        """Approval request with notes."""
        request = ApprovalRequest(admin_notes='Approved for VIP customer')
        assert request.admin_notes == 'Approved for VIP customer'

    def test_approval_without_notes(self):
        """Approval request without notes (should default to None)."""
        request = ApprovalRequest()
        assert request.admin_notes is None

    def test_approval_empty_notes(self):
        """Empty string notes allowed."""
        request = ApprovalRequest(admin_notes='')
        assert request.admin_notes == ''


class TestStatusCheckResponse:
    """Test StatusCheckResponse model."""

    def test_status_check_pending(self):
        """Status check for pending reservation."""
        response = StatusCheckResponse(
            id='res_001',
            status=ReservationStatus.PENDING,
            updated_at='2024-01-15T08:00:00',
        )
        assert response.id == 'res_001'
        assert response.status == ReservationStatus.PENDING

    def test_status_check_approved(self):
        """Status check for approved reservation."""
        response = StatusCheckResponse(
            id='res_001',
            status=ReservationStatus.APPROVED,
            admin_notes='Enjoy your parking!',
            updated_at='2024-01-15T08:30:00',
        )
        assert response.admin_notes == 'Enjoy your parking!'

    def test_status_check_rejected(self):
        """Status check for rejected reservation."""
        response = StatusCheckResponse(
            id='res_001',
            status=ReservationStatus.REJECTED,
            admin_notes='No spots available',
            updated_at='2024-01-15T08:30:00',
        )
        assert response.status == ReservationStatus.REJECTED
        assert response.admin_notes == 'No spots available'

    def test_status_check_serialization(self):
        """Test serialization with optional fields."""
        response = StatusCheckResponse(
            id='res_001',
            status=ReservationStatus.PENDING,
            updated_at='2024-01-15T08:00:00',
        )
        data = response.model_dump()
        assert 'id' in data
        assert 'status' in data
        assert 'updated_at' in data
        # Optional fields should be None
        assert data['admin_notes'] is None


class TestModelJsonSerialization:
    """Test JSON serialization/deserialization."""

    def test_request_from_json(self):
        """Create request from JSON data."""
        json_data = {
            'customer_name': 'John Doe',
            'car_number': 'ABC-1234',
            'parking_type': 'Standard',
            'start_time': '2024-01-15T09:00:00',
            'end_time': '2024-01-15T17:00:00',
        }
        request = ReservationRequest.model_validate(json_data)
        assert request.customer_name == 'John Doe'

    def test_response_to_json(self):
        """Convert response to JSON-serializable dict."""
        response = ReservationResponse(
            id='res_001',
            customer_name='John Doe',
            car_number='ABC-1234',
            parking_id=1,
            parking_type='Standard',
            start_time='2024-01-15T09:00:00',
            end_time='2024-01-15T17:00:00',
            total_price=24.0,
            status=ReservationStatus.PENDING,
            created_at='2024-01-15T08:00:00',
            updated_at='2024-01-15T08:00:00',
        )
        json_str = response.model_dump_json()
        assert '"id":"res_001"' in json_str
        assert '"status":"pending"' in json_str
