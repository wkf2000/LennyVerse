from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend_api.main import app, get_rag_service
from backend_api.rag_schemas import SearchResponse, SearchResult
from backend_api.rag_service import RagFilterValidationError


class _RankedFakeRagService:
    def search(
        self,
        query: str,
        *,
        k: int | None = None,
        filters: object | None = None,
    ) -> SearchResponse:
        return SearchResponse(
            query=query,
            results=[
                SearchResult(
                    id="chunk:podcast::a:0",
                    score=0.95,
                    title="Higher relevance",
                    guest="Ada Chen Rekhi",
                    date="2023-04-16",
                    tags=["growth"],
                    excerpt="First chunk excerpt.",
                    content_id="podcast::a",
                    chunk_index=0,
                ),
                SearchResult(
                    id="chunk:newsletter::b:1",
                    score=0.62,
                    title="Lower relevance",
                    guest=None,
                    date=None,
                    tags=[],
                    excerpt="Second chunk excerpt.",
                    content_id="newsletter::b",
                    chunk_index=1,
                ),
            ],
        )


class _EmptyFakeRagService:
    def search(
        self,
        query: str,
        *,
        k: int | None = None,
        filters: object | None = None,
    ) -> SearchResponse:
        return SearchResponse(query=query, results=[])


class _InvalidFilterFakeRagService:
    def search(
        self,
        query: str,
        *,
        k: int | None = None,
        filters: object | None = None,
    ) -> SearchResponse:
        raise RagFilterValidationError("Invalid date_from: 'not-a-date'. Expected format YYYY-MM-DD.")


def test_search_endpoint_returns_ranked_results() -> None:
    app.dependency_overrides[get_rag_service] = lambda: _RankedFakeRagService()
    client = TestClient(app)
    try:
        response = client.post("/api/search", json={"query": "product growth"})

        assert response.status_code == 200
        payload = response.json()
        assert payload["query"] == "product growth"
        results = payload["results"]
        assert len(results) == 2
        assert results[0]["score"] >= results[1]["score"]
        assert results[0]["id"] == "chunk:podcast::a:0"
        assert results[1]["id"] == "chunk:newsletter::b:1"
    finally:
        app.dependency_overrides.clear()


def test_search_endpoint_handles_empty_results() -> None:
    app.dependency_overrides[get_rag_service] = lambda: _EmptyFakeRagService()
    client = TestClient(app)
    try:
        response = client.post("/api/search", json={"query": "zzzznomatch"})

        assert response.status_code == 200
        payload = response.json()
        assert payload["query"] == "zzzznomatch"
        assert payload["results"] == []
    finally:
        app.dependency_overrides.clear()


def test_search_endpoint_returns_422_for_invalid_date_filter() -> None:
    app.dependency_overrides[get_rag_service] = lambda: _InvalidFilterFakeRagService()
    client = TestClient(app)
    try:
        response = client.post(
            "/api/search",
            json={
                "query": "product growth",
                "filters": {"date_from": "not-a-date"},
            },
        )

        assert response.status_code == 422
        payload = response.json()
        assert "Invalid date_from" in payload["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("query", ["", "   "])
def test_search_endpoint_rejects_empty_or_whitespace_query(query: str) -> None:
    app.dependency_overrides[get_rag_service] = lambda: _RankedFakeRagService()
    client = TestClient(app)
    try:
        response = client.post("/api/search", json={"query": query})

        assert response.status_code == 422
        payload = response.json()
        error_messages = [item["msg"] for item in payload["detail"]]
        assert any("query must not be empty or whitespace only" in msg for msg in error_messages)
    finally:
        app.dependency_overrides.clear()
