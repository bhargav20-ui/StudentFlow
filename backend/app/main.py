import json
import statistics
import uuid
import math
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .schemas import QueryRequest, DocumentRequest, CompareRequest
from .orchestrator import Orchestrator
from .storage import list_runs, load_documents, DATA_DIR

app = FastAPI(title="StudentFlow", description="Evidence-first autonomous multi-agent research assistant")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    from .config import GEMINI_API_KEY
    return {
        "status": "ok",
        "service": "StudentFlow API",
        "model_configured": bool(GEMINI_API_KEY),
    }

@app.post("/query")
def query(request: QueryRequest):
    try:
        return Orchestrator().run(request.question.strip(), request.mode)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="StudentFlow could not complete this request. Check the server logs and configuration.")

@app.post("/comparison")
def comparison(request: CompareRequest):
    # Runs the same question through the single-call baseline and proposed multi-agent workflow.
    baseline = Orchestrator().run(request.question.strip(), "single_agent")
    proposed = Orchestrator().run(request.question.strip(), "multi_agent")
    return {"question": request.question, "baseline": baseline, "multi_agent": proposed}

@app.get("/metrics")
def metrics():
    items = list_runs()
    if not items:
        return {"run_count": 0, "message": "No completed runs yet."}
    latencies = sorted(float(item.get("metrics", {}).get("latency_ms", 0)) for item in items)
    def avg(key):
        values = [item.get("metrics", {}).get(key) for item in items if isinstance(item.get("metrics", {}).get(key), (int, float))]
        return round(statistics.mean(values), 4) if values else None
    tool_calls = sum(item.get("metrics", {}).get("tool_calls", 0) for item in items)
    tool_successes = sum(item.get("metrics", {}).get("tool_successes", 0) for item in items)
    return {"run_count": len(items), "task_success_rate": avg("task_success"), "mean_latency_ms": avg("latency_ms"), "p95_latency_ms": latencies[min(len(latencies)-1, max(0, math.ceil(.95*len(latencies))-1))], "mean_groundedness": avg("groundedness"), "mean_evidence_coverage": avg("evidence_coverage"), "mean_hallucination_rate": avg("hallucination_rate"), "mean_tokens": avg("total_tokens"), "tool_success_rate": round(tool_successes / tool_calls, 4) if tool_calls else None}

@app.get("/mcp/tools")
async def mcp_tools():
    from .mcp_client import MCPToolClient
    try:
        tools = await MCPToolClient().list_tools()
        return {"status": "connected", "tools": tools, "count": len(tools)}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="MCP connection failed. Check that the MCP server and dependencies are available.")

@app.get("/documents")
def documents():
    return {"count": len(load_documents()), "documents": load_documents()}

@app.post("/documents")
def add_document(request: DocumentRequest):
    docs = load_documents()
    document_id = "DOC-" + uuid.uuid4().hex[:8].upper()
    item = {"document_id": document_id, "title": request.title.strip(), "source": request.source.strip(), "text": request.text.strip()}
    docs.append(item)
    (DATA_DIR / "documents.json").write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"message": "Document added to the searchable corpus.", "document": item, "count": len(docs)}

# Serve the plain HTML/CSS/JavaScript interface from the same Python app.
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="web")
