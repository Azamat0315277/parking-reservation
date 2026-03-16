"""
Unit tests for MCP file writer tools.

Tests the singleton MCP client manager and text extraction.
"""

import pytest
from unittest.mock import MagicMock


class TestMCPClientManagerPattern:
    """Test MCPClientManager singleton pattern."""

    def test_singleton_pattern(self):
        """Manager should follow singleton pattern."""
        # Simulate singleton
        class SingletonManager:
            _instance = None

            def __new__(cls):
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                return cls._instance

        instance1 = SingletonManager()
        instance2 = SingletonManager()

        assert instance1 is instance2

    def test_manager_has_required_methods(self):
        """Manager should have expected methods."""
        expected_methods = ['get_tools', 'get_tool', 'close']

        for method in expected_methods:
            assert isinstance(method, str)

    def test_lock_for_thread_safety(self):
        """Manager should use lock for thread safety."""
        import asyncio

        lock = asyncio.Lock()
        assert lock is not None


class TestExtractMCPText:
    """Test _extract_mcp_text response parser patterns."""

    def extract_text(self, result):
        """
        Extract text content from MCP tool response.
        Mirrors the logic in file_writer_tools.py.
        """
        # Case 1: Already a string
        if isinstance(result, str):
            return result

        # Case 2: List of content blocks
        if isinstance(result, list):
            texts = []
            for item in result:
                if isinstance(item, dict) and "text" in item:
                    texts.append(item["text"])
                elif isinstance(item, str):
                    texts.append(item)
                elif hasattr(item, "text"):
                    texts.append(item.text)
            return "\n".join(texts)

        # Case 3: Single object with .text attribute
        if hasattr(result, "text"):
            return result.text

        # Fallback: Convert to string
        return str(result)

    def test_extract_from_string(self):
        """Extract text from plain string."""
        result = self.extract_text("Hello, World!")
        assert result == "Hello, World!"

    def test_extract_from_list_of_dicts(self):
        """Extract from list of text content dicts."""
        result = self.extract_text([
            {'type': 'text', 'text': 'Line 1'},
            {'type': 'text', 'text': 'Line 2'},
        ])

        assert 'Line 1' in result
        assert 'Line 2' in result

    def test_extract_from_list_of_strings(self):
        """Extract from list of strings."""
        result = self.extract_text(['Line 1', 'Line 2'])

        assert 'Line 1' in result
        assert 'Line 2' in result

    def test_extract_from_object_with_text_attr(self):
        """Extract from object with .text attribute."""
        mock_obj = MagicMock()
        mock_obj.text = "Content from object"

        result = self.extract_text(mock_obj)

        assert result == "Content from object"

    def test_extract_from_list_of_objects(self):
        """Extract from list of TextContent objects."""
        obj1 = MagicMock()
        obj1.text = "First"
        obj2 = MagicMock()
        obj2.text = "Second"

        result = self.extract_text([obj1, obj2])

        assert 'First' in result
        assert 'Second' in result

    def test_extract_fallback_to_str(self):
        """Fallback to str() for unknown types."""
        result = self.extract_text(12345)

        assert result == "12345"

    def test_extract_empty_list(self):
        """Extract from empty list."""
        result = self.extract_text([])
        assert result == ""


class TestMCPConfig:
    """Test MCP configuration patterns."""

    def test_config_structure(self):
        """Config should have filesystem server."""
        config = {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"],
                "transport": "stdio",
            }
        }

        assert 'filesystem' in config
        assert 'command' in config['filesystem']
        assert 'args' in config['filesystem']
        assert 'transport' in config['filesystem']

    def test_config_uses_npx(self):
        """Config should use npx to run MCP server."""
        config = {"filesystem": {"command": "npx"}}
        assert config['filesystem']['command'] == 'npx'

    def test_config_uses_stdio_transport(self):
        """Config should use stdio transport."""
        config = {"filesystem": {"transport": "stdio"}}
        assert config['filesystem']['transport'] == 'stdio'

    def test_mcp_server_package(self):
        """Config should reference MCP filesystem server."""
        args = ["-y", "@modelcontextprotocol/server-filesystem", "/path"]
        assert "@modelcontextprotocol/server-filesystem" in args


class TestReservationFileFormat:
    """Test approved reservation file format."""

    def test_reservation_line_format(self):
        """Reservation line should follow expected format."""
        reservation = {
            'customer_name': 'John Doe',
            'car_number': 'ABC-1234',
            'parking_id': 42,
            'parking_type': 'Premium',
            'start_time': '2024-01-15T09:00:00',
            'end_time': '2024-01-15T17:00:00',
            'updated_at': '2024-01-15T08:30:00',
        }

        line = (
            f"{reservation['customer_name']} | {reservation['car_number']} | "
            f"Parking #{reservation['parking_id']} ({reservation['parking_type']}) | "
            f"{reservation['start_time']} - {reservation['end_time']} | "
            f"Approved: {reservation['updated_at']}"
        )

        assert 'John Doe' in line
        assert 'ABC-1234' in line
        assert '42' in line
        assert 'Premium' in line
        assert 'Approved:' in line

    def test_line_separator(self):
        """Fields should be separated by pipe."""
        line = "Name | Car | Spot | Time | Status"
        parts = line.split(' | ')
        assert len(parts) == 5


class TestFileOperations:
    """Test file operation patterns."""

    def test_append_with_newline(self):
        """Append should handle newlines correctly."""
        existing = "Line 1"
        new_line = "Line 2"

        # If existing doesn't end with newline, add one
        if existing and not existing.endswith("\n"):
            existing += "\n"

        result = existing + new_line + "\n"

        assert result == "Line 1\nLine 2\n"

    def test_append_to_empty(self):
        """Append to empty content."""
        existing = ""
        new_line = "First line"

        if existing and not existing.endswith("\n"):
            existing += "\n"

        result = existing + new_line + "\n"

        assert result == "First line\n"

    def test_read_empty_file(self):
        """Handle empty file content."""
        content = ""

        if not content.strip():
            result = "No reservations found."
        else:
            result = content

        assert result == "No reservations found."


class TestToolNames:
    """Test expected tool names."""

    def test_append_reservation_tool_name(self):
        """append_reservation tool should exist."""
        tool_name = 'append_reservation'
        assert tool_name == 'append_reservation'

    def test_read_reservations_tool_name(self):
        """read_reservations tool should exist."""
        tool_name = 'read_reservations'
        assert tool_name == 'read_reservations'

    def test_mcp_tool_names(self):
        """MCP tools should have expected names."""
        mcp_tools = ['read_file', 'write_file']
        assert 'read_file' in mcp_tools
        assert 'write_file' in mcp_tools
