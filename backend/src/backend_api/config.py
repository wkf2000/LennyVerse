from __future__ import annotations

from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

def _parse_cors_origins_csv(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    supabase_db_url: str | None = Field(default=None, alias="SUPABASE_DB_URL")
    cors_allow_origins_csv: str | None = Field(default=None, alias="CORS_ALLOW_ORIGINS")

    @computed_field
    @property
    def cors_allow_origins(self) -> list[str]:
        if self.cors_allow_origins_csv:
            return _parse_cors_origins_csv(self.cors_allow_origins_csv)
        return []

    def require_db_url(self) -> str:
        if not self.supabase_db_url:
            raise ValueError("SUPABASE_DB_URL is required to use graph endpoints.")
        return self.supabase_db_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
