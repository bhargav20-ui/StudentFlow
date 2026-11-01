# StudentFlow

StudentFlow is an evidence-first **autonomous multi-agent research and report assistant**. A user submits a research question; the orchestrator decides which agents to run. The agents plan subtasks, retrieve evidence through an MCP client/server, verify claims, write a source-grounded answer, and calculate run metrics.

## Why this is a genuine multi-agent use case

A research task benefits from separate responsibilities: decomposing a broad question, retrieving source material, checking claims against that material, writing only from verified claims, and evaluating the result. These stages can pass structured evidence and verification decisions to one another. The system is designed to expose failures rather than silently invent missing evidence.

## Simple technology stack

- **Python 3.12** — backend, orchestration, agents, MCP client/server, metrics and API.
- **FastAPI** — API and serves the interface.
- **Plain HTML, CSS and JavaScript** — small UI; no React, TypeScript, Node.js, or frontend build step.
- **Gemini API** — model calls; API key stays on the backend.
- **MCP Python SDK** — tool discovery and invocation across a separate MCP server process.
- **JSON, CSV and pytest** — local evidence corpus, run records, evaluation results and tests.

## Run on Windows / VS Code

1. Open the `StudentFlow` folder in VS Code.
2. Open a terminal and run:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

3. Open `backend/.env` and set `GEMINI_API_KEY` to your own key. Keep this file private. The default model is `gemini-3.8-flash`; change it only to a model available to your API account.
4. Start the app:

```powershell
uvicorn app.main:app --reload --port 8000
```

5. Open **http://127.0.0.1:8000**. API documentation is at **http://127.0.0.1:8000/docs** and health check at **http://127.0.0.1:8000/health**. No second terminal or frontend installation is required.

## Interface sections

1. **Research** — submit a question; inspect the actual workflow trace, answer, evidence, claim statuses and run metrics.
2. **Evaluation** — inspect metrics from saved runs, run the 30-case screening suite, and compare a single-agent baseline against multi-agent + MCP on the same question.
3. **Documents & MCP** — add text documents to the local searchable corpus and inspect the tools discovered from the MCP server.

Run history is stored in the backend but is not given a separate navigation tab. The most useful trace and evidence are shown directly with each research result.

## Tests and evaluation

```powershell
cd backend
pytest -q
```

The evaluation button runs 30 Gemini-backed cases and may consume API quota. It writes measured outputs to `backend/results/evaluation_suite.json` and `.csv`. A passing automated check is only a screening signal; manually inspect a sample. Compare baseline and multi-agent metrics across the same test set before making claims about improvement.

## Measurements and costs

Each run records the run ID, workflow events, MCP tool calls, latency, token usage when reported by Gemini, claim grounding, evidence coverage, unsupported/contradicted claim rate and task outcome. Exact API cost is left as **not configured** until you add verified per-million-token prices for the exact model to `.env`; the system must not pretend unknown cost is zero.

## Important limitations and safety

- The starter corpus is small and local. Add relevant source documents in **Documents & MCP** for useful domain research.
- The verifier and automated checks do not guarantee zero hallucinations. Evidence absence means the corpus is insufficient, not that a real-world claim is false.
- Added documents are saved to `backend/data/documents.json`; back up the file before replacing the corpus.
- This is a local academic demo. Before public deployment, add authentication/authorization for document management and administrative actions, request limits, timeouts, and suitable protection for MCP access. Never commit `.env` or publish API keys.
- Keep the MCP server separate from the reasoning/orchestration layer: MCP exposes capabilities; the orchestrator controls agent flow.

## Case-study requirements covered

- Planner, Researcher, Verifier, Writer and Evaluator roles.
- Automatic orchestration and shared run outputs.
- Separate MCP client and MCP server with tool discovery and calls.
- Search, document retrieval, safe arithmetic, evidence persistence and run-metric tools.
- 30 test cases including unknown questions, false premises, prompt injection and failure-related questions.
- Grounding, evidence coverage, unsupported-claim rate, latency, P95, tokens, cost configuration and tool success.
- Single-agent baseline comparison, `/health`, `/query`, `/metrics`, Dockerfile, source, README and tests.
