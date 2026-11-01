from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ROOT_DIR = _BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_ROOT_DIR / ".env", _BACKEND_DIR / ".env", ".env"),
        extra="ignore",
    )

    groq_api_key: str | None = None
    groq_model: str = "qwen/qwen3.8-27b"
    google_api_key: str | None = None
    gemini_model: str = "gemini-3.8-flash"
    hf_token: str | None = None
    hf_model: str = "Qwen/Qwen2.5-72B-Instruct"

    serpapi_api_key: str | None = None
    geoapify_api_key: str | None = None
    exchangerate_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("exchangerate_api_key", "exchange_rate_api_key", "exchangerate_key"),
    )

    db_path: str = "travel_agent.sqlite"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    user_agent: str = "ai-travel-agent/0.1 (portfolio project)"
    http_timeout: float = 15.0
    # Rough food/transport/activities spend, in USD; converted to the trip currency.
    daily_spend_usd_per_person: float = 60.0

    # Optional SMTP configuration for emailing itineraries
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "wayfinder@travel-agent.ai"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
