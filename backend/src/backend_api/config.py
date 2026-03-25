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

    openai_api_base: str | None = Field(default=None, alias="OPENAI_API_BASE")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    # Query-time embeddings: OpenAI-compatible API at Ollama (same as data pipeline ingest).
    ollama_embed_base_url: str = Field(
        default="http://localhost:11434/v1",
        alias="OLLAMA_EMBED_BASE_URL",
    )
    embedding_api_key: str = Field(default="ollama", alias="EMBEDDING_API_KEY")
    embedding_model: str = Field(default="embeddinggemma", alias="EMBEDDING_MODEL")

    rag_default_k: int = Field(default=8, alias="RAG_DEFAULT_K")
    rag_max_k: int = Field(default=32, alias="RAG_MAX_K")
    rag_retrieval_timeout_seconds: int = Field(default=30, alias="RAG_RETRIEVAL_TIMEOUT_SECONDS")
    rag_chat_timeout_seconds: int = Field(default=120, alias="RAG_CHAT_TIMEOUT_SECONDS")

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
