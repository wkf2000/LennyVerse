"""MCP server that exposes LennyVerse API endpoints as tools for AI agents (e.g. OpenClaw).

Run modes:
  stdio (default):  uv run python -m backend_api.mcp_server
  SSE (remote):     uv run python -m backend_api.mcp_server --sse --port 8001

Environment:
  LENNYVERSE_API_BASE  Base URL of the FastAPI server (default: http://localhost:8000)
  MCP_HOST             Bind address for SSE mode (default: 0.0.0.0)
  MCP_PORT             Port for SSE mode (default: 8001)
"""

from __future__ import annotations

import os

import httpx
from fastmcp import FastMCP

LENNYVERSE_API_BASE = os.environ.get("LENNYVERSE_API_BASE", "http://localhost:8000")
MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "8001"))

mcp = FastMCP(
    "LennyVerse",
    instructions=(
        "LennyVerse is an AI-powered product wisdom platform built on Lenny Rachitsky's "
        "newsletter and podcast corpus. Use these tools to search content, ask questions, "
        "explore the knowledge graph, and view publishing statistics."
    ),
)

_client = httpx.Client(base_url=LENNYVERSE_API_BASE, timeout=60.0)


def _api_get(path: str, params: dict | None = None) -> dict:
    resp = _client.get(path, params={k: v for k, v in (params or {}).items() if v is not None})
    resp.raise_for_status()
    return resp.json()


def _api_post(path: str, body: dict) -> dict:
    resp = _client.post(path, json=body)
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
def search(
    query: str,
    k: int | None = None,
    content_type: str | None = None,
    tags: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Semantic search over Lenny's Newsletter and Podcast corpus.

    Returns ranked results with title, excerpt, score, and metadata.
    Use content_type='podcast' or 'newsletter' to filter. Tags, date_from/date_to
    (YYYY-MM-DD) narrow results further.
    """
    body: dict = {"query": query}
    if k is not None:
        body["k"] = k
    filters = {}
    if content_type:
        filters["type"] = content_type
    if tags:
        filters["tags"] = tags
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to
    if filters:
        body["filters"] = filters
    return _api_post("/api/search", body)


@mcp.tool()
def ask(
    query: str,
    k: int | None = None,
    content_type: str | None = None,
) -> str:
    """Ask a question about Lenny's Newsletter/Podcast content using RAG.

    Returns a synthesized answer with citations. This calls the streaming chat
    endpoint and collects the full response.
    """
    body: dict = {"query": query}
    if k is not None:
        body["k"] = k
    if content_type:
        body["filters"] = {"type": content_type}

    with _client.stream("POST", "/api/chat", json=body) as resp:
        resp.raise_for_status()
        chunks: list[str] = []
        for line in resp.iter_lines():
            if line.startswith("data: "):
                import json

                payload = json.loads(line[6:])
                if "text_delta" in payload:
                    chunks.append(payload["text_delta"])
        return "".join(chunks)


@mcp.tool()
def get_knowledge_graph(
    node_types: list[str] | None = None,
    topic: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Get the LennyVerse knowledge graph (nodes and edges).

    Nodes are guests, topics, content items, and concepts. Filter by node_types
    (e.g. ['guest', 'topic']), topic name, or date range (YYYY-MM-DD).
    """
    params: dict = {}
    if node_types:
        params["nodeType"] = node_types
    if topic:
        params["topic"] = topic
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    return _api_get("/api/graph", params)


@mcp.tool()
def get_node_detail(node_id: str) -> dict:
    """Get detail for a specific knowledge graph node including connected nodes and related content."""
    return _api_get(f"/api/graph/nodes/{node_id}")


@mcp.tool()
def get_content_summary(content_id: str) -> dict:
    """Get a summary for a specific piece of content by its ID."""
    return _api_get(f"/api/content/{content_id}/summary")


@mcp.tool()
def get_topic_trends() -> dict:
    """Get topic trend data over time (quarterly counts) with a summary of the corpus."""
    return _api_get("/api/stats/topic-trends")


@mcp.tool()
def get_publishing_heatmap() -> dict:
    """Get publishing activity heatmap data (year/week grid of published content)."""
    return _api_get("/api/stats/heatmap")


@mcp.tool()
def get_content_breakdown() -> dict:
    """Get quarterly content breakdown by type (podcast vs newsletter) with word counts."""
    return _api_get("/api/stats/content-breakdown")


@mcp.tool()
def get_top_guests() -> dict:
    """Get the top podcast guests ranked by number of appearances."""
    return _api_get("/api/stats/top-guests")


@mcp.tool()
def generate_learning_outline(
    topic: str,
    num_weeks: int = 8,
    difficulty: str = "intermediate",
) -> dict:
    """Generate a multi-week learning outline for a product topic using the corpus.

    Difficulty can be 'intro', 'intermediate', or 'advanced'. Max 16 weeks.
    """
    return _api_post(
        "/api/generate/outline",
        {"topic": topic, "num_weeks": num_weeks, "difficulty": difficulty},
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LennyVerse MCP server")
    parser.add_argument("--sse", action="store_true", help="Run with SSE transport (for remote access)")
    parser.add_argument("--host", default=MCP_HOST, help="Bind host for SSE mode (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=MCP_PORT, help="Port for SSE mode (default: 8001)")
    args = parser.parse_args()

    if args.sse:
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        mcp.run()
