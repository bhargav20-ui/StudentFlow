from mcp.server.fastmcp import FastMCP
from app.mcp_tools import search_sources,get_document,safe_calculate,save_evidence,get_run_metrics
mcp=FastMCP("StudentFlow Capabilities")
@mcp.tool()
def search_sources_tool(query:str,limit:int=5)->dict:
    """Search the curated StudentFlow evidence corpus."""
    return {"items":search_sources(query,limit)}
@mcp.tool()
def get_document_tool(document_id:str)->dict:
    """Fetch a document by stable ID."""
    return get_document(document_id)
@mcp.tool()
def calculator_tool(expression:str)->dict:
    """Safely calculate basic arithmetic; arbitrary Python is not accepted."""
    try:return {"expression":expression,"result":safe_calculate(expression)}
    except Exception as e:return {"error":str(e)}
@mcp.tool()
def save_evidence_tool(run_id:str,evidence:list[dict])->dict:
    """Persist evidence records for a workflow run."""
    return save_evidence(run_id,evidence)
@mcp.tool()
def get_run_metrics_tool(run_id:str)->dict:
    """Read metrics for a completed workflow run."""
    return get_run_metrics(run_id)
if __name__=="__main__":mcp.run()
