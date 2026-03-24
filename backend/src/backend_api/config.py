from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    supabase_db_url: str | None = Field(default=None, alias="SUPABASE_DB_URL")
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173"],
        alias="CORS_ALLOW_ORIGINS",
    )

    def require_db_url(self) -> str:
        if not self.supabase_db_url:
            raise ValueError("SUPABASE_DB_URL is required to use graph endpoints.")
        return self.supabase_db_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
