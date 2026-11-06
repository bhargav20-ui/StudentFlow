# StudentFlow

StudentFlow is an evidence-first **multi-agent research assistant**. A user submits a research question; the system plans research subtasks, retrieves source documents through MCP, verifies claims against evidence, writes a grounded answer and records run metrics.

## Core workflow

1. **Planner** — decomposes the question into focused research subtasks.
2. **Researcher** — discovers and calls MCP search capabilities to retrieve source material.
3. **Verifier** — checks factual claims and their evidence references.
4. **Writer** — answers using verified claims and clearly reports evidence gaps.
5. **Evaluator** — calculates groundedness, evidence coverage, unsupported-claim rate and task outcome for each run.
6. **Orchestrator** — coordinates the agents, records workflow events and handles controlled failures.

The separate MCP server exposes only two capabilities: searching the curated corpus and retrieving a full document by ID.

## Technology

- Python 3.12, FastAPI and Pydantic
- Gemini API (backend only)
- MCP Python SDK with a stdio client/server
- Plain HTML, CSS and JavaScript; no frontend build step
- JSON document corpus, JSON run records, CSV metrics and pytest
- Docker and Render deployment configuration

## Run locally on Windows

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Add your own `GEMINI_API_KEY` to `backend/.env`. Keep the file private.

Start the application:

```powershell
uvicorn app.main:app --reload --port 8000
```

Open the UI at http://127.0.0.1:8000. API docs are at http://127.0.0.1:8000/docs and health is at http://127.0.0.1:8000/health.

## Interface

- **Research** — submit a question and inspect the answer, workflow trace, evidence, claim checks and per-run metrics.
- **Insights** — inspect aggregate metrics from saved runs and compare the single-agent baseline with multi-agent + MCP on the same question.
- **Documents & MCP** — add source text, inspect the knowledge corpus and discover the two MCP research tools.

## Tests

```powershell
cd backend
pytest -q
```

The tests cover corpus search, document lookup, Gemini retry classification, cost arithmetic and evaluation edge cases. They do not make Gemini-backed research calls.

## Measurements

Each run records its ID, workflow events, retrieved evidence, verified claims, MCP tool outcomes, latency and model-reported token usage. Estimated API cost is shown only when verified per-million-token prices for the configured model have been supplied. Unknown cost is not reported as zero.

The Insights page compares the baseline and multi-agent workflow. A single run is illustrative, not a statistically reliable benchmark. Use a representative golden set, repeated runs, trajectory checks and human review before claiming an improvement.

## Data and deployment

- Starter sources: `backend/data/documents.json`.
- Runtime records: the configured `STUDENTFLOW_DATA_DIR` with `data/` and `results/` subfolders.
- Deployment: see [DEPLOY_RENDER.md](DEPLOY_RENDER.md). The root Dockerfile is the Render build target; the MCP server runs as a local subprocess inside the same service.

## Safety and limitations

- Retrieved content is untrusted data, never instructions.
- Unsupported claims must not be presented as facts. Missing evidence means the available corpus is insufficient, not that a claim is false.
- The local starter corpus is small; add relevant sources for useful research.
- This is a controlled academic demonstration, not a hardened public multi-user service. Add authentication, authorization, rate limits and protected administrative access before exposing write endpoints publicly.
- Never commit `.env`, API keys or private credentials.
