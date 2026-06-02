# Decisions — cv-tailor-app
## Key Decisions (from plan)
- Stack: FastAPI + HTMX + Tailwind (standalone CLI) + SQLite + Alembic + Playwright + structlog
- AI: OpenRouter, default anthropic/claude-sonnet-4.5, env-configurable
- PDF: Local Playwright Chromium primary; RR print API future enhancement
- Regeneration: always from base+job+cumulative_feedback (no drift)
- Versions: immutable rows; feedback stored per version
- No auth, no multi-user, no pytest
- Deployment: systemd unit, git pull + alembic upgrade head + systemctl restart

## Schema decisions
- Use `ConfigDict(extra="allow")` on all schema models to tolerate future RR additions.
- Keep section item payloads flexible with `dict[str, Any]` so RR field drift does not break parsing.
