# StudentFlow

**Evidence-first multi-agent research assistant**

StudentFlow turns a research question into a structured workflow: plan the investigation, retrieve source material through MCP, verify claims against retrieved evidence, write a cited answer, and calculate quality and performance metrics.

> A successful API response is not automatically a successful research answer. StudentFlow reports workflow execution and answer quality as separate outcomes.

## How it works

1. **Planner agent** — decomposes a research question into focused, searchable subtasks.
2. **Researcher agent** — discovers a compatible search tool from MCP metadata and retrieves source documents.
3. **Verifier agent** — extracts material claims and classifies them as SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, or CONTRADICTED.
4. **Writer agent** — writes from verified claims, cites evidence IDs, and falls back to a deterministic claim summary if generated citations are missing or invalid.
5. **Evaluator agent** — calculates claim-level evidence metrics and validates answer citation IDs.
6. **Orchestrator** — coordinates stages, records timing and usage, handles failures, and saves each run.

The single-agent mode is available as a baseline. It retrieves evidence and asks the model to answer in one generation call; it is not the same pipeline as multi-agent mode.

## Architecture

```text
Browser (HTML / CSS / JavaScript)
              |
              v
        FastAPI backend
              |
         Orchestrator
              |
     +--------+---------+
     |        |         |
  Planner  Researcher  Verifier
              |         |
              v         v
          MCP client   Gemini
              |
       stdio MCP server
              |
       Searchable corpus
              |
           Writer
              |
          Evaluator
              |
       Run JSON + CSV metrics
```

## Technology

- Python 3.12, FastAPI and Pydantic
- Google Gemini API through the Google GenAI SDK
- MCP Python SDK; backend launches the MCP server as a local stdio subprocess
- Plain HTML, CSS and JavaScript frontend; no frontend build step
- JSON document corpus and run records, CSV evaluation history
- pytest and GitHub Actions for backend validation
- Render native Python deployment configuration

## Metrics and evaluation

| Metric | Meaning |
|---|---|
| Groundedness | Share of extracted claims labelled supported and linked to an existing evidence ID |
| Evidence coverage | Share of extracted claims linked to at least one existing evidence ID |
| Hallucination rate | Share of claims labelled unsupported/contradicted or lacking a valid evidence link |
| Citation validity | Share of parsed answer citation IDs that resolve to retrieved evidence IDs |
| Task success | Whether a non-empty answer meets the evaluator's current success/abstention rules |
| Pipeline execution success | Whether the workflow avoided an orchestrator failure and all recorded MCP calls succeeded |
| Retrieval success | Whether the run returned at least one evidence record |
| Agent completion rate | Share of expected stages that recorded a completed or warning event |
| Latency | End-to-end wall-clock duration of a run |
| P95 latency | 95th percentile of recorded end-to-end run latencies |
| Tokens | Input/output token counts reported by the model SDK |
| Estimated cost | Calculated only when input and output prices are configured for the selected model |
| MCP tool success | Successful recorded tool calls divided by recorded tool calls |
| Model retries | Additional attempts made after transient model API errors |

**Interpret metrics carefully:** citation validity checks whether an ID exists in retrieved evidence; it does not prove semantic support. Groundedness is based on verifier classifications, not an independent human truth assessment. If no claims are extracted, claim-level metrics are null (not applicable), not zero. A safe insufficient-evidence response can be successful abstention while retrieval or pipeline execution is unsuccessful. P95 from a small sample is indicative only. A single comparison is not a statistically reliable benchmark.

## Gemini reliability and error handling

Gemini may temporarily return rate-limit or availability errors such as 429, 500, 502, 503, or 504. StudentFlow retries recognised transient errors with exponential backoff. Defaults: four total attempts, 1.5-second base delay, and 12-second maximum delay.

- GEMINI_MAX_ATTEMPTS — total attempts, bounded to 1–6 (default 4).
- GEMINI_RETRY_BASE_SECONDS — initial backoff in seconds (default 1.5).
- GEMINI_RETRY_MAX_SECONDS — maximum backoff in seconds (default 12).

Authentication, invalid configuration, and other non-transient errors are not retried. If transient failures continue, the run stops safely with a temporary-unavailability message. The system must not invent an answer to hide a model outage. Retry attempts and backoff time are recorded when available. Retries increase total latency; they do not make the provider respond faster.

## Run locally

Requirements: Python 3.12 and a Gemini API key.

### Windows PowerShell

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit backend/.env and set your own GEMINI_API_KEY. Do not commit this file.

Start the application from the backend directory:

```powershell
uvicorn app.main:app --reload --port 8000
```

- UI: http://127.0.0.1:8000/
- Health: http://127.0.0.1:8000/health
- API docs: http://127.0.0.1:8000/docs
- MCP tools: http://127.0.0.1:8000/mcp/tools
- Aggregate metrics: http://127.0.0.1:8000/metrics

## Configuration

Copy backend/.env.example to backend/.env for local development.

| Variable | Required | Description |
|---|---:|---|
| GEMINI_API_KEY | Yes | Gemini API key; keep it server-side |
| GEMINI_MODEL | No | Model enabled for the API account; default gemini-2.5-flash |
| GEMINI_MAX_ATTEMPTS | No | Total attempts for transient errors; default 4 |
| GEMINI_RETRY_BASE_SECONDS | No | Exponential backoff base delay; default 1.5 |
| GEMINI_RETRY_MAX_SECONDS | No | Backoff delay cap; default 12 |
| GEMINI_INPUT_PRICE_PER_1M | No | Verified input price in USD per million tokens |
| GEMINI_OUTPUT_PRICE_PER_1M | No | Verified output price in USD per million tokens |
| STUDENTFLOW_DATA_DIR | No | Runtime directory for documents and results |
| STUDENTFLOW_MAX_RESEARCH_TASKS | No | Maximum planner subtasks |
| STUDENTFLOW_RESULTS_PER_TASK | No | Requested search result count per subtask |
| STUDENTFLOW_MAX_EVIDENCE_ITEMS | No | Maximum unique evidence records per run |

The MCP server is launched by the backend as a local subprocess. Its dependencies are installed from `backend/requirements.txt`.

## Use the application

- **Research** — submit a question and inspect the answer, warnings, workflow trace, retrieved evidence, verified claims and per-run metrics.
- **Insights** — inspect aggregate measurements and compare the single-agent baseline with multi-agent + MCP using the same question. Repeat each question for meaningful comparisons.
- **Documents & MCP** — add source text, inspect the searchable corpus, and check MCP connectivity and discovered tools. More documents alone do not guarantee relevant evidence.

## Automated testing

Run backend tests locally:

```powershell
cd backend
pytest -q
```

Tests use deterministic fixtures and mocked model/MCP responses for agent and orchestration behaviour. They cover agent output validation, evidence ID handling, citation checks, evaluator edge cases, corpus functions, Gemini retry classification and retry behaviour.

The GitHub Actions workflow at .github/workflows/studentflow-validation.yml installs backend dependencies and runs pytest on pushes and pull requests targeting main.

Automated tests do not prove live Gemini availability, live MCP deployment health, semantic correctness of generated answers, or production latency. Those require live integration and manual acceptance tests.

## Manual acceptance testing

Before each run, record the expected facts and acceptable evidence for the exact question.

| Field | What to record |
|---|---|
| Test ID | Stable identifier, e.g. SF-001 |
| Input | Exact research question |
| Expected result | Required facts, scope and acceptable sources |
| Execution status | PASS / FAIL for agent, model and MCP execution |
| Output status | PASS / FAIL against expected answer |
| Evidence quality | Relevance, sufficiency and traceability of sources |
| Groundedness / coverage | Reported values plus claim-level review |
| Citation validity | Whether cited IDs exist and support the associated statement |
| Latency | End-to-end time, retries and retry wait |
| Diagnosis | Failed stage and reason |
| Regression status | Re-run result after a fix |

Keep execution and answer quality separate:

- **Execution PASS + Output PASS:** workflow ran and answer met the expected result.
- **Execution PASS + Output FAIL:** agents ran, but the answer was incomplete, irrelevant, incorrect or inadequately supported.
- **Execution FAIL + Output FAIL:** a component or dependency prevented completion.
- **Execution FAIL + safe abstention:** system refused to guess, but the requested research task was not completed.

After a fix, rerun the failed case and relevant regression tests. Do not mark a test passed solely because the endpoint returned HTTP 200 or the UI displayed an answer.

## Deployment

See [DEPLOY_RENDER.md](DEPLOY_RENDER.md) for Render native Python deployment instructions.

- Render uses its native Python runtime with `backend/` as the service root.
- FastAPI serves both the API and frontend.
- The MCP server runs as a local stdio subprocess in the same service.
- Set GEMINI_API_KEY as a hosting secret and choose a model enabled for that API account.
- The free-plan configuration uses ephemeral `/tmp` storage; uploaded documents and run history can be lost on restart or redeploy. Use a supported persistent disk if durable storage is required.

## Known limitations and safety

- Retrieved source content is untrusted data, never instructions to agents.
- Verifier classifications are model-generated. Valid evidence IDs alone do not guarantee semantic entailment.
- Citation-ID validation does not independently establish source relevance or factual truth.
- Search quality depends on the available MCP tools and corpus contents.
- Gemini availability, quota, model access and latency depend on the provider and API account.
- Token usage and pricing metadata may be unavailable; unknown cost is not reported as zero.
- This is an academic demonstration, not a hardened public multi-user service. Add authentication, authorization, rate limits, request-size controls and protected administrative access before exposing write endpoints publicly.
- Never commit .env, API keys or private credentials.

## Repository

[StudentFlow on GitHub](https://github.com/bhargav20-ui/StudentFlow)
