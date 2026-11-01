# StudentFlow — deploy-ready package

StudentFlow is an evidence-first multi-agent research assistant built with Python 3.12, FastAPI, Gemini, an MCP stdio server/client, and a plain HTML/CSS/JavaScript interface.

## Deploy

See [`DEPLOY_RENDER.md`](DEPLOY_RENDER.md). The repository includes a root `Dockerfile` and `render.yaml` Blueprint.

## Run locally

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Add GEMINI_API_KEY and confirm GEMINI_MODEL in backend/.env
uvicorn app.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000`.

## Run tests

```powershell
cd backend
pytest -q
```

The full evaluation suite invokes Gemini and may consume API quota. Run it intentionally from the Evaluation screen.

## Persistent data

Set `STUDENTFLOW_DATA_DIR` to a writable persistent directory. The app creates `data/` and `results/` there and seeds `data/documents.json` from the bundled starter corpus on first startup.

## Security boundary

This package is suitable for a controlled academic demo. It is not yet a public multi-user production service: add authentication, authorization, rate limiting and admin protection before exposing write/evaluation endpoints to untrusted users. Keep API credentials in host secret settings.
