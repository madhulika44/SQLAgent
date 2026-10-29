"""
Application settings, loaded from the `.env` file in the repository root.

pydantic-settings reads each field from an environment variable with the
same name (case-insensitive): `db_server` <- DB_SERVER, and so on. Values
are converted to the declared type (e.g. "3" -> 3, "true" -> True) and the
app refuses to start if a value is invalid - much better than discovering
a typo halfway through a demo.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py -> parents[2] is the repository root, where .env lives.
REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",          # .env also holds seed-only settings (DB_ADMIN_*)
    )

    # --- SQL Server (read-only login) ---
    db_server: str = "localhost"
    db_name: str = "FoodDeliveryDB"
    db_driver: str = "ODBC Driver 18 for SQL Server"
    db_trust_server_certificate: str = "yes"
    db_readonly_user: str = "sql_agent_reader"
    # SecretStr hides the value when settings are printed or logged.
    db_readonly_password: SecretStr = SecretStr("")

    # --- LLM providers ---
    llm_provider: Literal["groq", "gemini"] = "groq"
    llm_fallback_enabled: bool = True
    groq_api_key: SecretStr = SecretStr("")
    groq_model: str = "openai/gpt-oss-120b"
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-3.5-flash-lite"
    llm_temperature: float = 0.0
    llm_timeout_seconds: int = 30

    # --- Agent behaviour ---
    agent_max_retries: int = 3
    agent_max_rows: int = 200
    query_timeout_seconds: int = 30
    schema_sample_max_distinct: int = 20

    # --- API (Phase 4) ---
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS_ORIGINS is a comma-separated string in .env; the API needs a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Load settings once and reuse them (reading .env on every call would be wasteful)."""
    return Settings()
