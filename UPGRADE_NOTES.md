# StudentFlow audit and hardening notes

## Preserved
- Existing FastAPI + plain HTML/CSS/JavaScript architecture.
- Gemini model service and five agent roles.
- Separate MCP client/server boundary.
- Existing local corpus, run records, comparison flow and evaluation suite.

## Changes in this package
- Removed the bundled virtual environment and private `.env` from the distributable archive.
- Replaced the credential-like value accidentally present in `.env.example` with a placeholder. Rotate that key if it was real and has been shared.
- Hardened the arithmetic tool with AST complexity limits, numeric bounds, finite-result checks and clearer validation errors.
- Added validation for MCP run IDs before constructing evidence/metrics file paths.
- Added validation for search query and result limit inputs.
- Corrected task-success scoring so an empty-evidence run is successful only when the system explicitly abstains, rather than merely returning any answer.
- Corrected P95 aggregation to use the nearest-rank percentile index.
- Avoided returning raw internal exception details from the query and MCP API endpoints.
- Added pytest path configuration and regression tests for calculator/path validation.

## Verification performed here
- Python compile check passed for application, MCP server and tests.
- Direct calculator positive and negative checks passed.
- Full pytest suite could not be executed in this environment because the MCP dependency is not installed and package installation is unavailable (network/DNS restricted). Run `pip install -r requirements.txt` followed by `pytest -q` in the project's Python 3.12 environment.

## Before public deployment
- Add authentication and authorization to document management and administrative/evaluation endpoints.
- Add request rate limits, bounded execution time, and deployment-specific CORS origins.
- Configure the Gemini key only in local `.env` or the hosting provider's secret manager.
- Pin and verify the MCP SDK version against its current official documentation.
- Re-run the full 30-case suite and manually audit a sample before reporting metrics.
