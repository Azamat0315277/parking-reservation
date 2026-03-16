"""
Pytest configuration and shared fixtures for parking reservation tests.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def mock_db_engine():
    """Mock SQLAlchemy engine for database tests."""
    engine = MagicMock()
    connection = MagicMock()
    result = MagicMock()

    engine.connect.return_value.__enter__ = MagicMock(return_value=connection)
    engine.connect.return_value.__exit__ = MagicMock(return_value=False)
    connection.execute.return_value = result

    return engine, connection, result


@pytest.fixture
def sample_parking_spots():
    """Sample parking spot data for testing."""
    return [
        {
            'parking_id': 1,
            'parking_type': 'regular',
            'hourly_rate': 3.0,
            'space_availability': True,
            'reservation_start': None,
            'reservation_end': None,
        },
        {
            'parking_id': 2,
            'parking_type': 'premium',
            'hourly_rate': 5.0,
            'space_availability': True,
            'reservation_start': None,
            'reservation_end': None,
        },
        {
            'parking_id': 3,
            'parking_type': 'ev_charging',
            'hourly_rate': 4.0,
            'space_availability': False,
            'reservation_start': datetime.now(),
            'reservation_end': datetime.now() + timedelta(hours=2),
        },
        {
            'parking_id': 4,
            'parking_type': 'handicap',
            'hourly_rate': 2.0,
            'space_availability': True,
            'reservation_start': None,
            'reservation_end': None,
        },
    ]


# ============================================================================
# Reservation Fixtures
# ============================================================================

@pytest.fixture
def sample_reservation_request():
    """Sample reservation request data."""
    return {
        'parking_id': 1,
        'parking_type': 'regular',
        'customer_name': 'John Doe',
        'car_number': 'ABC-1234',
        'start_time': (datetime.now() + timedelta(hours=1)).isoformat(),
        'end_time': (datetime.now() + timedelta(hours=3)).isoformat(),
    }


@pytest.fixture
def sample_pending_reservations():
    """Sample pending reservations for testing."""
    base_time = datetime.now()
    return {
        'reservations': [
            {
                'id': 'res_001',
                'customer_name': 'John Doe',
                'car_number': 'ABC-1234',
                'parking_id': 1,
                'parking_type': 'regular',
                'start_time': (base_time + timedelta(hours=1)).isoformat(),
                'end_time': (base_time + timedelta(hours=3)).isoformat(),
                'status': 'pending',
                'created_at': base_time.isoformat(),
            },
            {
                'id': 'res_002',
                'customer_name': 'Jane Smith',
                'car_number': 'XYZ-5678',
                'parking_id': 2,
                'parking_type': 'premium',
                'start_time': (base_time + timedelta(hours=2)).isoformat(),
                'end_time': (base_time + timedelta(hours=5)).isoformat(),
                'status': 'pending',
                'created_at': base_time.isoformat(),
            },
        ]
    }


# ============================================================================
# PII Test Data Fixtures
# ============================================================================

@pytest.fixture
def pii_test_cases():
    """Test cases for PII detection."""
    return {
        'ssn': [
            ('My SSN is 123-45-6789', True),
            ('SSN: 123456789', True),
            ('Not an SSN: 000-00-0000', False),  # Invalid SSN
            ('Phone looks like SSN: 555-12-3456', True),
        ],
        'credit_card': [
            ('Visa: 4111111111111111', True),
            ('MC: 5500000000000004', True),
            ('Amex: 340000000000009', True),
            ('Not a CC: 1234567890', False),
        ],
        'email': [
            ('Contact: john.doe@example.com', True),
            ('Email me at user@domain.co.uk', True),
            ('Not email: john@', False),
        ],
        'phone': [
            ('Call me: (555) 123-4567', True),
            ('Phone: 555-123-4567', True),
            ('Mobile: +1 555 123 4567', True),
            ('Not phone: 12345', False),
        ],
        'ip_address': [
            ('Server IP: 192.168.1.1', True),
            ('Address: 10.0.0.255', True),
            ('Invalid IP: 999.999.999.999', False),
        ],
    }


# ============================================================================
# MCP Fixtures
# ============================================================================

@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for file operations testing."""
    client = AsyncMock()

    # Mock tools
    read_tool = AsyncMock()
    write_tool = AsyncMock()

    read_tool.name = 'read_file'
    write_tool.name = 'write_file'

    client.get_tools = AsyncMock(return_value=[read_tool, write_tool])

    return client, read_tool, write_tool


# ============================================================================
# LLM Fixtures
# ============================================================================

@pytest.fixture
def mock_llm():
    """Mock LLM for agent tests."""
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content="Test response")
    return llm


@pytest.fixture
def mock_embeddings():
    """Mock embeddings model."""
    embeddings = MagicMock()
    embeddings.embed_query.return_value = [0.1] * 768
    embeddings.embed_documents.return_value = [[0.1] * 768]
    return embeddings


# ============================================================================
# API Test Fixtures
# ============================================================================

@pytest.fixture
def api_client():
    """Create test client for FastAPI."""
    from fastapi.testclient import TestClient
    from src.api.main import app

    return TestClient(app)


# ============================================================================
# Ground Truth Fixtures
# ============================================================================

@pytest.fixture
def sample_ground_truth():
    """Sample ground truth data for evaluation tests."""
    return {
        'test_cases': [
            {
                'id': 'tc_001',
                'category': 'operating_hours',
                'question': 'What are the parking operating hours?',
                'ground_truth': 'The parking facility operates 24/7.',
                'ground_truth_contexts': ['Operating Hours: 24/7'],
            },
            {
                'id': 'tc_002',
                'category': 'pricing',
                'question': 'What is the hourly rate for regular parking?',
                'ground_truth': 'Regular parking costs $3 per hour.',
                'ground_truth_contexts': ['Regular parking: $3/hour'],
            },
        ]
    }


# ============================================================================
# Workflow State Fixtures
# ============================================================================

@pytest.fixture
def sample_parking_state():
    """Sample ParkingState for workflow tests."""
    return {
        'messages': [],
        'classification': None,
        'reservation_data': None,
        'approval_status': None,
        'admin_notes': None,
        'interaction_mode': 'cli',
    }


# ============================================================================
# Environment Setup
# ============================================================================

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock environment variables for all tests."""
    monkeypatch.setenv('GOOGLE_API_KEY', 'test-api-key')
    monkeypatch.setenv('READER_CONNECTION_STRING', 'postgresql://test:test@localhost/test')
    monkeypatch.setenv('WRITER_CONNECTION_STRING', 'postgresql://test:test@localhost/test')
    monkeypatch.setenv('MONGODB_URI', 'mongodb://localhost:27017')
    monkeypatch.setenv('ALLOWED_DIR', '/tmp/test')


# ============================================================================
# Utility Functions
# ============================================================================

def create_mock_row(data: Dict[str, Any]):
    """Create a mock database row that supports both index and attribute access."""
    class MockRow:
        def __init__(self, data):
            self._data = data
            for key, value in data.items():
                setattr(self, key, value)

        def __getitem__(self, key):
            return self._data[key]

        def _mapping(self):
            return self._data

    return MockRow(data)


def create_mock_result(rows: List[Dict[str, Any]]):
    """Create a mock database result set."""
    mock_rows = [create_mock_row(row) for row in rows]
    result = MagicMock()
    result.fetchall.return_value = mock_rows
    result.fetchone.return_value = mock_rows[0] if mock_rows else None
    result.__iter__ = lambda self: iter(mock_rows)
    return result
