# Testing report

The included unit tests cover safe calculator behavior, rejection of Python code in arithmetic input, corpus search, evaluation-suite case count, and the cost formula example.

Run tests locally with:

```powershell
cd backend
pytest -q
```

The 30-case Gemini-backed evaluation is separate from unit tests because it requires a configured API key and can consume quota. Its output must be generated on the user's machine; no pre-filled result is presented as a live measurement. Automated expected-behavior checks are a screening aid and should be supplemented by manual review.
