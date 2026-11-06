from mcp.server.fastmcp import FastMCP

from app.mcp_tools import get_document, search_sources

mcp = FastMCP("StudentFlow Research")


@mcp.tool()
def search_sources_tool(query: str, limit: int = 5) -> dict:
    """Search the curated StudentFlow knowledge corpus for relevant source documents."""
    return {"items": search_sources(query, limit)}


@mcp.tool()
def get_document_tool(document_id: str) -> dict:
    """Retrieve the full text and source metadata for one document by document ID."""
    return get_document(document_id)


if __name__ == "__main__":
    mcp.run()
