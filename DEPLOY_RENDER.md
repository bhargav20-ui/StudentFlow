# Deploy StudentFlow to Render

## What this package includes

- Root-level Dockerfile (Render can build from the repository root).
- `render.yaml` Blueprint with `/health` health check and a persistent disk.
- FastAPI serves both the API and the plain HTML/CSS/JavaScript frontend.
- MCP server is launched as a local stdio subprocess by the backend; it is not a separate public service.

## Before deploying

1. Push the contents of this folder to a GitHub repository.
2. Create a Render account and choose **New → Blueprint**.
3. Connect the repository containing `render.yaml`.
4. In the Blueprint environment settings, provide `GEMINI_API_KEY` as a secret.
5. Confirm `GEMINI_MODEL` is a model currently available to your Gemini API account. The supplied value is a starting default, not a guarantee of account availability.
6. Deploy the service and wait for the `/health` check to pass.

Render provisions a persistent disk at `/var/data`; StudentFlow stores its document corpus and run/evaluation records there. The disk is configured in `render.yaml` and requires a paid Render service plan.

## Verify deployment

- Open `https://YOUR-SERVICE.onrender.com/` for the UI.
- Open `/health` and confirm `status` is `ok` and `model_configured` is `true`.
- Open `/docs` to inspect the API.
- Submit a small research query using a question supported by the starter corpus.
- Check `/metrics` and `/mcp/tools`.

## Important security note

This is a deployable academic demonstration, not a hardened public multi-tenant service. Before sharing it widely, add authentication and authorization to document-management and evaluation endpoints, rate limiting, request-size controls, and protected administrative access. Do not expose `/docs` publicly if your deployment requires a private API. Never put the Gemini key in frontend code or commit `.env`.

## Local Docker test

```bash
docker build -t studentflow .
docker run --rm -p 8000:8000 \
  -e GEMINI_API_KEY="YOUR_KEY" \
  -e GEMINI_MODEL="YOUR_AVAILABLE_MODEL" \
  -v studentflow-data:/var/data \
  studentflow
```

Then visit `http://localhost:8000/` and `http://localhost:8000/health`.
