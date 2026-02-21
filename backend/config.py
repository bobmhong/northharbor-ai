"""Application configuration loaded from environment variables."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    auth0_domain: str = ""
    auth0_api_audience: str = ""
    auth0_algorithms: str = "RS256"

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "northharbor_ai"

    app_env: str = "development"
    log_level: str = "info"

    rate_limit_default: str = "60/minute"
    rate_limit_expensive: str = "10/minute"
    llm_provider: str = "ollama"
    llm_model: str = "llama3.1:8b-instruct-q4_K_M"
    ollama_base_url: str = "http://localhost:11434"
    ollama_timeout_seconds: float = 120.0
    openai_api_key: str = Field(default="", validation_alias="NORTHHARBOR_OPENAPI_KEY")
    openai_base_url: str = "https://api.openai.com/v1"
    openai_timeout_seconds: float = 45.0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def auth0_jwks_url(self) -> str:
        return f"https://{self.auth0_domain}/.well-known/jwks.json"

    @property
    def auth0_issuer(self) -> str:
        return f"https://{self.auth0_domain}/"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
