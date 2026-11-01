# Gemini model fix

The previous build defaulted to `gemini-2.5-flash`, which may be unavailable for newly created Gemini API projects. This build defaults to `gemini-3.8-flash`.

If you already have a `.env` file, update its `GEMINI_MODEL` line too:

```env
GEMINI_MODEL=gemini-3.8-flash
```

Restart Uvicorn after changing `.env`. Visit `http://127.0.0.1:8000/docs` to see the FastAPI API routes. The root URL can return `{"detail":"Not Found"}` if no root route is defined; that alone does not mean the server is down.
