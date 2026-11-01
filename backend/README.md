# Backend and local run guide

The interface is served by FastAPI from `app/static`; there is no separate frontend process.

## Windows / VS Code

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `GEMINI_API_KEY` in `.env`, then start the application:

```powershell
uvicorn app.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000`. API docs: `http://127.0.0.1:8000/docs`. Health: `http://127.0.0.1:8000/health`.

## Test

```powershell
pytest -q
```

The evaluation suite can be run from the UI or with `POST /evaluation/run`. It makes 30 model-backed runs and may consume Gemini quota. Results are stored in `results/evaluation_suite.json` and `results/evaluation_suite.csv`.
