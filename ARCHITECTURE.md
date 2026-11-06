# StudentFlow architecture

StudentFlow is an evidence-first multi-agent research assistant. It accepts a research question, searches the connected knowledge corpus through MCP, checks claims against retrieved evidence, writes a grounded response, and records measured run metrics.

## Core components

1. **Interface** — plain HTML, CSS and JavaScript served by FastAPI.
2. **Orchestrator** — controls the workflow, shares structured results, records events and handles failures.
3. **Agents** — Planner, Researcher, Verifier, Writer and Evaluator. The Evaluator calculates metrics from the run; it does not invent quality scores.
4. **MCP capability layer** — a separate MCP client and stdio server expose only source search and full-document retrieval.
5. **Model service** — Gemini API calls remain on the backend; credentials are read from environment variables.
6. **Memory and data** — curated source documents, per-run JSON records and an aggregate CSV metrics log.

## Main workflow

User question → Planner → Researcher → MCP client → MCP server → source search / document retrieval → Verifier → Writer → Evaluator → answer, evidence, claims and metrics.

The workflow may return an insufficient-evidence response or a controlled warning when retrieval or a component fails. Retrieved document text is untrusted data, never an instruction. The user does not manually select agents.

## Supported modes

- **Multi-agent + MCP** — planning, retrieval, claim verification, writing and evaluation.
- **Single-agent baseline** — comparison baseline using the same MCP retrieval capability and a single answer-generation call.

The comparison endpoint runs the same question through both modes. A single comparison is illustrative; repeated runs on a representative test set are needed before claiming measured improvement.

## API routes

- `GET /health` — service and model configuration status.
- `POST /query` — run a research question.
- `POST /comparison` — compare single-agent and multi-agent modes on the same question.
- `GET /metrics` — aggregate metrics from recorded runs.
- `GET /mcp/tools` — discover tools exposed by the MCP server.
- `GET /documents`, `POST /documents` — inspect or add source documents.

## Data and deployment

- `backend/data/documents.json` contains the starter evidence corpus.
- Run records and `evaluation_results.csv` are written under the configured data directory.
- The root `Dockerfile` and `render.yaml` are the deployment configuration. The MCP server runs as a local stdio subprocess inside the backend container.
- Gemini credentials stay in backend environment variables or hosting-provider secrets.

## Scope boundaries

StudentFlow is a research assistant, not an email, calendar, CRM, code-writing or general task-automation agent. It does not need arithmetic tools, external write actions, approval workflows for business side effects, or a separate benchmark-suite UI. Keep the system focused on source-grounded research, transparent evidence, reliable orchestration and honest evaluation.
