from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM
    llm_provider: str = "perplexity"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.perplexity.ai"
    anthropic_api_key: str = ""
    llm_model: str = "sonar"
    llm_max_tokens: int = 4096
    llm_timeout_seconds: int = 60

    # Database
    database_url: str = "sqlite+aiosqlite:///./job_hunter.db"

    # App
    app_env: str = "development"
    app_debug: bool = True
    app_secret_key: str = "change-me"
    log_level: str = "INFO"

    # Telegram
    telegram_bot_token: str = ""

    # Extraction
    extractor_timeout_seconds: int = 15
    extractor_max_content_bytes: int = 500_000

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def normalized_database_url(self) -> str:
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        return self.database_url

    @property
    def resolved_llm_api_key(self) -> str:
        return self.llm_api_key or self.anthropic_api_key

    @property
    def has_llm_api_key(self) -> bool:
        return bool(self.resolved_llm_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
