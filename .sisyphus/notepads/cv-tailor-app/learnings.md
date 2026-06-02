# Learnings — cv-tailor-app
# Scaffold notes
- Used `uv sync` with direct `pyproject.toml` authoring; this was the cleanest way to pin the FastAPI + ruff scaffold without extra init churn.
- `uv sync` on a fresh workspace resolved and installed Playwright, SQLAlchemy, and Ruff cleanly.
- Health endpoint verified with a live uvicorn process and curl.
