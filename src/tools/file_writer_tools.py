import os
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

def extract_text(result) -> str:
    """Extract text from MCP tool result."""
    if isinstance(result, str):
        return result
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
    if hasattr(result, "text"):
        return result.text
    return str(result)

@tool
async def append_reservation(reservation_line: str) -> str:
    """
    Append a new reservation line to the approved_reservations.txt file.
    Use this tool ONLY after admin approval is confirmed.
    
    Args:
        reservation_line: Reservation in format 'Name | Car Number | Period | Approval Time'
                          Example: 'John Smith | ABC-1234 | 2025-01-28 09:00 - 2025-01-28 18:00 | 2025-01-28 08:45:32'
    
    Returns:
        Success or error message
    """
    filename = "approved_reservations.txt"
    
    client = MultiServerMCPClient(MCP_CONFIG)
    tools = await client.get_tools()
    
    read_tool = next(t for t in tools if t.name == "read_file")
    write_tool = next(t for t in tools if t.name == "write_file")
    
    full_path = f"{ALLOWED_DIR}/{filename}"
    
    # Read existing
    try:
        raw_result = await read_tool.ainvoke({"path": full_path})
        existing = extract_text(raw_result)
    except Exception:
        existing = ""
    
    # Append
    if existing and not existing.endswith("\n"):
        existing += "\n"
    updated = existing + reservation_line + "\n"
    
    # Write
    await write_tool.ainvoke({"path": full_path, "content": updated})
    
    return f"✓ Reservation appended: {reservation_line}"


@tool
async def read_reservations() -> str:
    """
    Read all approved reservations from file.
    Use this to check existing reservations or verify a new entry was added.
    
    Returns:
        All reservation entries or message if empty
    """
    filename = "approved_reservations.txt"
    
    client = MultiServerMCPClient(MCP_CONFIG)
    tools = await client.get_tools()
    
    read_tool = next(t for t in tools if t.name == "read_file")
    full_path = f"{ALLOWED_DIR}/{filename}"
    
    try:
        raw_result = await read_tool.ainvoke({"path": full_path})
        content = extract_text(raw_result)
        
        if not content.strip():
            return "No reservations found."
        
        return f"Approved reservations:\n{content}"
    except Exception as e:
        return f"Error reading file: {str(e)}"