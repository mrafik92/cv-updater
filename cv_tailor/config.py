"""Application settings for CV Tailor."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_host: str = Field(default="127.0.0.1", validation_alias="APP_HOST")
    app_port: int = Field(default=8000, validation_alias="APP_PORT")
    database_url: str = Field(
        default="sqlite:///data/cv_tailor.db", validation_alias="DATABASE_URL"
    )
    openrouter_api_key: SecretStr = Field(validation_alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(
        default="anthropic/claude-sonnet-4.5", validation_alias="OPENROUTER_MODEL"
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1", validation_alias="OPENROUTER_BASE_URL"
    )
    rr_base_url: str = Field(validation_alias="RR_BASE_URL")
    rr_api_token: SecretStr = Field(validation_alias="RR_API_TOKEN")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    pdf_timeout_seconds: int = Field(
        default=60, validation_alias="PDF_TIMEOUT_SECONDS"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
