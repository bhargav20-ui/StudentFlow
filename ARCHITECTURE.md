# StudentFlow architecture (plain-language version)

## Five layers

1. **Interface** — plain HTML/CSS/JavaScript page served by FastAPI. Three sections: Research, Evaluation, Documents & MCP.
2. **Orchestration** — Python coordinates the workflow and records a shared run result.
3. **Agents** — Planner creates subtasks; Researcher retrieves source material; Verifier labels claims; Writer creates the answer; Evaluator calculates metrics.
4. **Capabilities** — an MCP client discovers and invokes tools on a separate MCP server: source search, document lookup, safe calculator, evidence saving, and run metrics.
5. **Memory/data** — curated documents in JSON, per-run JSON, evaluation JSON/CSV and application logs.

## Main research flow

User question → Planner → Researcher → MCP client → MCP server/tools → Verifier → Writer → Evaluator → answer + evidence + metrics.

The exact path may stop early or return a controlled warning if evidence is missing or a component fails. The user does not manually choose agents. The separate single-agent baseline exists only to support the required experiment.

## Main API routes

- `GET /health` — health check.
- `POST /query` — run a research task (`multi_agent` by default; `single_agent` is the baseline).
- `POST /comparison` — run the same question through baseline and proposed workflows.
- `GET /metrics` — aggregate recorded run metrics.
- `GET /mcp/tools` — connect to the MCP server and discover its tools.
- `GET /documents`, `POST /documents` — list or add corpus documents.
- `POST /evaluation/run`, `GET /evaluation/results` — run and read the 30-case suite.

## Notes

- Gemini credentials remain on the backend.
- The local corpus is intentionally small; retrieval quality depends on the documents added.
- A metric is a measured estimate, not proof that every answer is correct.
