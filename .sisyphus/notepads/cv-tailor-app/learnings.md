## T6: structlog JSON + contextvars pattern used

## T2: pydantic-settings config module
- Pydantic Settings v2 loads config from env vars cleanly with `env_prefix=""` and `SecretStr` for API tokens.
- `get_settings()` is the only construction path, so config stays cached and import-time side effects stay zero.
