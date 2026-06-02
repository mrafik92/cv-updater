## T6: structlog JSON + contextvars pattern used

## T2: pydantic-settings config module
- Pydantic Settings v2 loads config from env vars cleanly with `env_prefix=""` and `SecretStr` for API tokens.
- `get_settings()` is the only construction path, so config stays cached and import-time side effects stay zero.
- Added sync SQLAlchemy/Alembic SQLite baseline with config-driven database URL and timestamp/index/constraint coverage.
- SQLite JSON columns were mapped through SQLAlchemy JSON type; migration stores them as TEXT-compatible columns in SQLite.
- Alembic round-trip validated with upgrade -> downgrade base -> upgrade head against data/cv_tailor.db.
