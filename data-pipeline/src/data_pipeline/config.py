from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    supabase_db_url: str | None = Field(default=None, alias="SUPABASE_DB_URL")
    embedding_base_url: str = Field(default="http://localhost:11434/v1", alias="OLLAMA_EMBED_BASE_URL")
    embedding_api_key: str = Field(default="ollama", alias="EMBEDDING_API_KEY")
    embedding_model: str = Field(default="embeddinggemma", alias="EMBEDDING_MODEL")
    embedding_dimensions: int = Field(default=768, alias="EMBEDDING_DIMENSIONS")
    embedding_batch_size: int = Field(default=64, alias="EMBEDDING_BATCH_SIZE")

    ingest_chunk_size_chars: int = Field(default=1000, alias="INGEST_CHUNK_SIZE_CHARS")
    ingest_chunk_overlap_chars: int = Field(default=100, alias="INGEST_CHUNK_OVERLAP_CHARS")

    summarize_api_base: str | None = Field(default=None, alias="SUMMARIZE_API_BASE")
    summarize_api_key: str | None = Field(default=None, alias="SUMMARIZE_API_KEY")
    summarize_model: str | None = Field(default=None, alias="SUMMARIZE_MODEL")
    summarize_max_chars: int = Field(default=8000, alias="SUMMARIZE_MAX_CHARS")

    data_root: Path = Field(
        default=Path("data/lennys-newsletterpodcastdata"),
        alias="DATASET_ROOT_DIR",
    )

    @property
    def index_path(self) -> Path:
        return self.data_root / "index.json"

    @property
    def newsletters_dir(self) -> Path:
        return self.data_root / "newsletters"

    @property
    def podcasts_dir(self) -> Path:
        return self.data_root / "podcasts"

    def require_db_url(self) -> str:
        if not self.supabase_db_url:
            raise ValueError("SUPABASE_DB_URL is required for non-dry-run operations.")
        return self.supabase_db_url

    def require_summarize_config(self) -> tuple[str, str, str]:
        missing = []
        if not self.summarize_api_base:
            missing.append("SUMMARIZE_API_BASE")
        if not self.summarize_api_key:
            missing.append("SUMMARIZE_API_KEY")
        if not self.summarize_model:
            missing.append("SUMMARIZE_MODEL")
        if missing:
            raise ValueError(f"{', '.join(missing)} required for summarization.")
        return self.summarize_api_base, self.summarize_api_key, self.summarize_model  # type: ignore[return-value]
