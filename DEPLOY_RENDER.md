# Deploy StudentFlow to Render (native Python)

StudentFlow runs directly on Render's native Python runtime. Docker is not required.

## Deploy

1. Push the repository to GitHub.
2. In Render, choose **New → Blueprint** and connect this repository.
3. Render reads the root-level `render.yaml`. The service uses `backend/` as its root directory.
4. Provide `GEMINI_API_KEY` as a secret in the Blueprint environment settings.
5. Confirm `GEMINI_MODEL` is available to your Gemini API account.
6. Deploy and wait for the `/health` check to pass.

The Blueprint installs dependencies from `backend/requirements.txt` and starts FastAPI with Uvicorn. The application serves its frontend from the same process. The MCP server is launched by the backend as a local stdio subprocess using the same Python environment; it is not a separate public service.

## Storage note

The current free-plan configuration stores runtime data under `/tmp/studentflow-data`. Treat this storage as ephemeral: documents added through the UI and recorded run history may be lost when the service restarts or is redeployed. The starter document corpus is copied into the runtime data directory when it is first initialized.

If persistent storage is required, choose a Render plan that supports a persistent disk, attach one, and set `STUDENTFLOW_DATA_DIR` to its mount path (for example, `/var/data`).

## Verify deployment

- Open `https://YOUR-SERVICE.onrender.com/` for the UI.
- Open `/health` and confirm `status` is `ok` and `model_configured` is `true`.
- Submit a small research query supported by the starter corpus.
- Check `/metrics` to confirm run records are being written.

## Security

This is an academic demonstration, not a hardened public multi-tenant service. Before sharing widely, add authentication and authorization to document-management endpoints, rate limiting, request-size controls, and protected administrative access. Never put the Gemini key in frontend code or commit `.env`.

## Local development

Use Python 3.12 and follow the local setup in the root README. Docker is not needed for local development or the Render deployment.
