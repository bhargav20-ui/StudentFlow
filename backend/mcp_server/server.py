from mcp.server.fastmcp import FastMCP

from app.mcp_tools import get_document, search_sources_with_status

mcp = FastMCP("StudentFlow Research")


@mcp.tool()
def search_sources_tool(query: str, limit: int = 5) -> dict:
    """Search biomedical literature and local notes with source-status metadata."""
    # search_sources already returns the MCP payload: {items, source_status}.
    # Do not wrap it in another items object or the Researcher cannot see documents.
    return search_sources_with_status(query, limit)


@mcp.tool()
def get_document_tool(document_id: str) -> dict:
    """Retrieve the full text and source metadata for one document by document ID."""
    return get_document(document_id)


if __name__ == "__main__":
    mcp.run()
