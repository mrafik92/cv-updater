## T6: structlog JSON + contextvars pattern used

## T2: pydantic-settings config module
- Pydantic Settings v2 loads config from env vars cleanly with `env_prefix=""` and `SecretStr` for API tokens.
- `get_settings()` is the only construction path, so config stays cached and import-time side effects stay zero.
- Added sync SQLAlchemy/Alembic SQLite baseline with config-driven database URL and timestamp/index/constraint coverage.
- SQLite JSON columns were mapped through SQLAlchemy JSON type; migration stores them as TEXT-compatible columns in SQLite.
- Alembic round-trip validated with upgrade -> downgrade base -> upgrade head against data/cv_tailor.db.

## T11 — tailor.py
- `Resume` Pydantic model uses `extra="allow"` everywhere (RRBaseModel) — JSON Schema must mirror with `additionalProperties: true` at every level so any LLM output that round-trips through `Resume.model_validate` is also schema-valid.
- `JobInput.description` is the only required field; `title`/`company` optional, included in user prompt only when present.
- `build_user_prompt` always appends a regenerate-from-base reminder so feedback never causes drift onto a previous tailored output.
- `tailor()` retries exactly once on `ValidationError`, appending the validation error to the prompt; second failure propagates.
- `OpenRouterClient` import is `TYPE_CHECKING`-only — module imports cleanly even though `cv_tailor/services/openrouter.py` does not yet exist (T-?).
- `jsonschema` was not in `pyproject.toml`; added via `uv add jsonschema`.

## T9 — RR v5 API Client (2026-06-02)

### Endpoints used
- `GET /api/rpc/resumes`       → `resume.list` (metadata, no `data` field)
- `GET /api/rpc/resumes/{id}`  → `resume.getById` (full resume incl. `data`)
- `GET /api/rpc/resumes/{id}/pdf` → streams PDF directly (no separate signed-URL step when using API key)

### Auth
- `x-api-key` header is the primary / highest-priority method in RR v5.
- `Authorization: Bearer` works too but is lower priority.

### Field mapping
- RR returns `name` and `updatedAt` (camelCase); we expose `title` and `updated_at` via `_normalise_resume_meta`.

### Retry strategy
- Single retry on 5xx only, 0.5 s sleep. No retry on 4xx.

### Virtualenv
- Project uses `.venv/` — invoke as `.venv/bin/python` not system python.

### Stub server
- Port 9911, auto-kills after 60 s.
- Routes: `/api/rpc/resumes`, `/api/rpc/resumes/r1`, `auth-fail` (401), `unavailable` (503).

## T10 — OpenRouterClient
- `httpx.AsyncClient` used as async context manager inside the method (not stored on self) — keeps the client stateless and avoids connection-pool leaks across requests.
- Retry loop appends assistant + user correction messages to the conversation so the model sees its own bad output before retrying.
- `json_schema` response_format with `strict: true` enforces structured output on compatible models.
- Evidence: `.sisyphus/evidence/task-10-import.txt` — import exits 0.

## T13 — repository layer
- `db.flush()` is enough to materialize PKs for newly created Job/Generation/Version rows before commit.
- `get_or_create_generation` should key idempotency on `(job_id, base_resume_id)` so repeated calls reuse the same generation row.
- `version_number` must be derived from the latest version within a generation, not from the global table.
