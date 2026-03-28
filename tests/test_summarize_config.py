import pytest

from data_pipeline.config import Settings


def test_summarize_fields_default_to_none() -> None:
    settings = Settings(
        SUPABASE_DB_URL="postgresql://localhost/test",
        DATASET_ROOT_DIR="/tmp/fake",
    )
    assert settings.summarize_api_base is None
    assert settings.summarize_api_key is None
    assert settings.summarize_model is None
    assert settings.summarize_max_chars == 8000


def test_summarize_fields_from_env(monkeypatch) -> None:
    monkeypatch.setenv("SUMMARIZE_API_BASE", "https://api.example.com/v1")
    monkeypatch.setenv("SUMMARIZE_API_KEY", "sk-test")
    monkeypatch.setenv("SUMMARIZE_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("SUMMARIZE_MAX_CHARS", "4000")
    settings = Settings(
        SUPABASE_DB_URL="postgresql://localhost/test",
        DATASET_ROOT_DIR="/tmp/fake",
    )
    assert settings.summarize_api_base == "https://api.example.com/v1"
    assert settings.summarize_api_key == "sk-test"
    assert settings.summarize_model == "gpt-4o-mini"
    assert settings.summarize_max_chars == 4000


def test_require_summarize_config_raises_when_missing() -> None:
    settings = Settings(
        SUPABASE_DB_URL="postgresql://localhost/test",
        DATASET_ROOT_DIR="/tmp/fake",
    )
    with pytest.raises(ValueError, match="SUMMARIZE_API_BASE.*SUMMARIZE_API_KEY.*SUMMARIZE_MODEL"):
        settings.require_summarize_config()


def test_require_summarize_config_returns_tuple() -> None:
    settings = Settings(
        SUPABASE_DB_URL="postgresql://localhost/test",
        DATASET_ROOT_DIR="/tmp/fake",
        SUMMARIZE_API_BASE="https://api.example.com/v1",
        SUMMARIZE_API_KEY="sk-test",
        SUMMARIZE_MODEL="gpt-4o-mini",
    )
    base, key, model = settings.require_summarize_config()
    assert base == "https://api.example.com/v1"
    assert key == "sk-test"
    assert model == "gpt-4o-mini"
