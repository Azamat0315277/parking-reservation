"""
MCP-based file operations for parking reservations.

Uses the Model Context Protocol (MCP) filesystem server to manage
the approved_reservations.txt file with a singleton client pattern
to prevent resource leaks.
"""

import os
import asyncio
from typing import Optional, List, Any
from langchain.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from dotenv import load_dotenv

load_dotenv()

ALLOWED_DIR = os.getenv("ALLOWED_DIR")

MCP_CONFIG = {
    "filesystem": {
        "command": "npx",
        "args": [
            "-y",
            "@modelcontextprotocol/server-filesystem",
            ALLOWED_DIR
        ],
        "transport": "stdio",
    }
}


class MCPClientManager:
    """
    Singleton manager for MCP client connections.

    Prevents resource leaks by reusing a single client instance
    across all tool invocations instead of creating a new client
    on every call.
    """

    _instance: Optional["MCPClientManager"] = None
    _client: Optional[MultiServerMCPClient] = None
    _tools: Optional[List[Any]] = None
    _lock: asyncio.Lock = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._lock = asyncio.Lock()
        return cls._instance

    async def get_tools(self) -> List[Any]:
        """
        Get MCP tools, initializing the client if needed.

        Returns cached tools if already initialized, otherwise
        creates the client connection and retrieves tools.
        """
        async with self._lock:
            if self._tools is None:
                self._client = MultiServerMCPClient(MCP_CONFIG)
                self._tools = await self._client.get_tools()
            return self._tools

    async def get_tool(self, name: str) -> Any:
        """Get a specific tool by name."""
        tools = await self.get_tools()
        for tool in tools:
            if tool.name == name:
                return tool
        raise ValueError(f"Tool '{name}' not found in MCP tools")

    async def close(self):
        """Close the client connection and reset state."""
        async with self._lock:
            if self._client is not None:
                # MCP client cleanup if needed
                self._client = None
                self._tools = None


# Global singleton instance
_mcp_manager = MCPClientManager()


def _extract_mcp_text(result: Any) -> str:
    """
    Extract text content from MCP tool response.

    MCP tools can return responses in multiple formats depending on
    the operation and server implementation:
    - Plain string: Direct file content
    - List of TextContent objects: [{type: "text", text: "..."}]
    - Object with .text attribute: TextContent dataclass

    This function normalizes all formats to a plain string.

    Args:
        result: Raw MCP tool response

    Returns:
        Extracted text content as a string
    """
    # Case 1: Already a string
    if isinstance(result, str):
        return result

    # Case 2: List of content blocks (common MCP response format)
    if isinstance(result, list):
        texts = []
        for item in result:
            if isinstance(item, dict) and "text" in item:
                # Dict with text key: {"type": "text", "text": "content"}
                texts.append(item["text"])
            elif isinstance(item, str):
                # Plain string in list
                texts.append(item)
            elif hasattr(item, "text"):
                # TextContent object with .text attribute
                texts.append(item.text)
        return "\n".join(texts)

    # Case 3: Single object with .text attribute
    if hasattr(result, "text"):
        return result.text

    # Fallback: Convert to string
    return str(result)


@tool
async def append_reservation(reservation_line: str) -> str:
    """
    Append a new reservation line to the approved_reservations.txt file.
    Use this tool ONLY after admin approval is confirmed.

    Args:
        reservation_line: Reservation in format:
            'Name | Car Number | Parking #ID (Type) | Period | Approved: Timestamp'
            Example: 'John Smith | ABC-1234 | Parking #42 (Premium) |
                      2025-01-28 09:00 - 2025-01-28 18:00 | Approved: 2025-01-28T08:45:32'

    Returns:
        Success or error message
    """
    filename = "approved_reservations.txt"
    full_path = f"{ALLOWED_DIR}/{filename}"

    # Get tools from singleton manager (no resource leak)
    read_tool = await _mcp_manager.get_tool("read_file")
    write_tool = await _mcp_manager.get_tool("write_file")

    # Read existing content
    try:
        raw_result = await read_tool.ainvoke({"path": full_path})
        existing = _extract_mcp_text(raw_result)
    except Exception:
        # File doesn't exist yet, start fresh
        existing = ""

    # Append new reservation with proper newline handling
    if existing and not existing.endswith("\n"):
        existing += "\n"
    updated = existing + reservation_line + "\n"

    # Write updated content
    await write_tool.ainvoke({"path": full_path, "content": updated})

    return f"Reservation appended: {reservation_line}"


@tool
async def read_reservations() -> str:
    """
    Read all approved reservations from file.
    Use this to check existing reservations or verify a new entry was added.

    Returns:
        All reservation entries or message if empty/error
    """
    filename = "approved_reservations.txt"
    full_path = f"{ALLOWED_DIR}/{filename}"

    # Get read tool from singleton manager
    read_tool = await _mcp_manager.get_tool("read_file")

    try:
        raw_result = await read_tool.ainvoke({"path": full_path})
        content = _extract_mcp_text(raw_result)

        if not content.strip():
            return "No reservations found."

        return f"Approved reservations:\n{content}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


async def cleanup_mcp_client():
    """
    Cleanup function to close MCP client connection.
    Call this during application shutdown.
    """
    await _mcp_manager.close()
