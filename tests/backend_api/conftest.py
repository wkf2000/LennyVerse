from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend_api.main import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def rag_dependency_override_registry() -> Any:
    """Register FastAPI dependency overrides for RAG services (wire targets in Task 3+)."""

    keys: list[Any] = []

    class _Registry:
        def set(self, dependency: Any, factory: Callable[[], Any]) -> None:
            app.dependency_overrides[dependency] = factory
            keys.append(dependency)

    reg = _Registry()
    yield reg
    for dep in keys:
        app.dependency_overrides.pop(dep, None)


@pytest.fixture
def fake_rag_service_factory() -> Callable[[], Any]:
    """Deterministic fake RAG service for tests once RAG deps are exposed on the app."""

    def _make() -> Any:
        class _FakeRagService:
            id = "fake-rag-deterministic"

        return _FakeRagService()

    return _make


@pytest.fixture
def unset_rag_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "OPENAI_API_BASE",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "OPENAI_EMBEDDING_MODEL",
        "RAG_DEFAULT_K",
        "RAG_MAX_K",
        "RAG_RETRIEVAL_TIMEOUT_SECONDS",
        "RAG_CHAT_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(key, raising=False)
