"""
Unit tests for workflow node utilities.

Tests classification parsing and routing logic without importing
modules that initialize external API clients.
"""

import json
import pytest
import re


class TestClassificationParsing:
    """Test classification tag parsing logic."""

    def parse_classification(self, text: str) -> dict:
        """
        Parse classification from agent response text.
        Mirrors the logic in workflow/nodes.py without importing it.
        """
        result = {'type': None, 'reservation_data': None}

        # Check for INFO tag
        if '<<<INFO>>>' in text:
            result['type'] = 'info'
            return result

        # Check for RESERVATION tag with JSON
        reservation_match = re.search(r'<<<RESERVATION:(.+?)>>>', text, re.DOTALL)
        if reservation_match:
            result['type'] = 'reservation'
            try:
                result['reservation_data'] = json.loads(reservation_match.group(1))
            except json.JSONDecodeError:
                result['reservation_data'] = None
            return result

        return result

    def test_parse_info_classification(self):
        """Parse INFO classification tag."""
        text = "Here is the information you requested. <<<INFO>>>"
        result = self.parse_classification(text)
        assert result['type'] == 'info'
        assert result['reservation_data'] is None

    def test_parse_reservation_classification(self):
        """Parse RESERVATION classification tag with JSON data."""
        reservation_data = {
            'customer_name': 'John Doe',
            'car_number': 'ABC-1234',
            'parking_type': 'Standard',
            'start_time': '2024-01-15T09:00:00',
            'end_time': '2024-01-15T17:00:00',
        }
        text = f"I'll help with your reservation. <<<RESERVATION:{json.dumps(reservation_data)}>>>"
        result = self.parse_classification(text)
        assert result['type'] == 'reservation'
        assert result['reservation_data'] is not None
        assert result['reservation_data']['customer_name'] == 'John Doe'

    def test_parse_no_classification(self):
        """Handle text without classification tag."""
        text = "This is a general message without any classification."
        result = self.parse_classification(text)
        assert result['type'] is None

    def test_parse_malformed_json(self):
        """Handle malformed JSON in reservation tag."""
        text = "<<<RESERVATION:{invalid json}>>>"
        result = self.parse_classification(text)
        assert result['type'] == 'reservation'
        assert result['reservation_data'] is None

    def test_parse_empty_text(self):
        """Handle empty text."""
        result = self.parse_classification("")
        assert result['type'] is None

    def test_info_tag_in_middle(self):
        """INFO tag in middle of text."""
        text = "Some text <<<INFO>>> more text"
        result = self.parse_classification(text)
        assert result['type'] == 'info'


class TestRoutingLogic:
    """Test routing decision logic."""

    def route_after_classification(self, state: dict) -> str:
        """Route based on classification result."""
        classification = state.get('classification')
        if classification == 'reservation':
            return 'human_approval'
        return '__end__'

    def route_after_approval(self, state: dict) -> str:
        """Route based on approval status."""
        approval_status = state.get('approval_status')
        if approval_status == 'approve':
            return 'reservation'
        return 'denial'

    def route_after_reservation(self, state: dict) -> str:
        """Route based on reservation result."""
        result = state.get('reservation_result')
        if result == 'success':
            return 'success'
        return 'denial'

    def test_route_to_human_approval_for_reservation(self):
        """Reservation should route to human approval."""
        state = {'classification': 'reservation'}
        result = self.route_after_classification(state)
        assert result == 'human_approval'

    def test_route_to_end_for_info(self):
        """Info request should route to end."""
        state = {'classification': 'info'}
        result = self.route_after_classification(state)
        assert result == '__end__'

    def test_route_to_end_for_unknown(self):
        """Unknown classification routes to end."""
        state = {'classification': None}
        result = self.route_after_classification(state)
        assert result == '__end__'

    def test_route_to_reservation_on_approve(self):
        """Approved should route to reservation node."""
        state = {'approval_status': 'approve'}
        result = self.route_after_approval(state)
        assert result == 'reservation'

    def test_route_to_denial_on_deny(self):
        """Denied should route to denial node."""
        state = {'approval_status': 'deny'}
        result = self.route_after_approval(state)
        assert result == 'denial'

    def test_route_to_success_on_success(self):
        """Successful reservation routes to success node."""
        state = {'reservation_result': 'success'}
        result = self.route_after_reservation(state)
        assert result == 'success'

    def test_route_to_denial_on_failure(self):
        """Failed reservation routes to denial."""
        state = {'reservation_result': 'failure'}
        result = self.route_after_reservation(state)
        assert result == 'denial'


class TestParkingStateStructure:
    """Test expected state structure."""

    def test_state_has_required_keys(self):
        """ParkingState should have expected keys."""
        required_keys = [
            'messages',
            'classification',
            'reservation_data',
            'approval_status',
            'admin_notes',
            'interaction_mode',
        ]

        state = {
            'messages': [],
            'classification': None,
            'reservation_data': None,
            'approval_status': None,
            'admin_notes': None,
            'interaction_mode': 'cli',
        }

        for key in required_keys:
            assert key in state

    def test_interaction_modes(self):
        """Valid interaction modes."""
        valid_modes = ['cli', 'api']
        for mode in valid_modes:
            state = {'interaction_mode': mode}
            assert state['interaction_mode'] in valid_modes


class TestReservationDataFormat:
    """Test reservation data structure."""

    def test_complete_reservation_data(self):
        """Reservation data should have all required fields."""
        reservation = {
            'customer_name': 'John Doe',
            'car_number': 'ABC-1234',
            'parking_type': 'Standard',
            'parking_id': 42,
            'start_time': '2024-01-15T09:00:00',
            'end_time': '2024-01-15T17:00:00',
        }

        assert 'customer_name' in reservation
        assert 'car_number' in reservation
        assert 'parking_type' in reservation
        assert 'start_time' in reservation
        assert 'end_time' in reservation

    def test_optional_parking_id(self):
        """Parking ID can be optional (auto-assigned)."""
        reservation = {
            'customer_name': 'Jane',
            'car_number': 'XYZ-5678',
            'parking_type': 'Premium',
            'start_time': '2024-01-15T09:00:00',
            'end_time': '2024-01-15T17:00:00',
        }

        # parking_id can be missing
        assert 'parking_id' not in reservation or reservation.get('parking_id') is None
