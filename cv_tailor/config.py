from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    database_url: str = "sqlite:///data/cv_tailor.db"
    openrouter_api_key: SecretStr = Field(default_factory=lambda: SecretStr("dummy"))
    openrouter_model: str = "anthropic/claude-sonnet-4.5"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    rr_base_url: str = "http://localhost"
    rr_api_token: SecretStr = Field(default_factory=lambda: SecretStr("dummy"))
    log_level: str = "INFO"
    pdf_timeout_seconds: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
    )



@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
