"""Smoke tests for the LennyVerse MCP server tool registration."""

from __future__ import annotations

import asyncio

import pytest

from backend_api.mcp_server import mcp


EXPECTED_TOOLS = [
    "search",
    "ask",
    "get_knowledge_graph",
    "get_node_detail",
    "get_content_summary",
    "get_topic_trends",
    "get_publishing_heatmap",
    "get_content_breakdown",
    "get_top_guests",
    "generate_learning_outline",
]


@pytest.fixture()
def tool_names() -> list[str]:
    tools = asyncio.run(mcp.list_tools())
    return [t.name for t in tools]


def test_all_tools_registered(tool_names: list[str]) -> None:
    for expected in EXPECTED_TOOLS:
        assert expected in tool_names, f"Tool '{expected}' not registered"


def test_tool_count(tool_names: list[str]) -> None:
    assert len(tool_names) == len(EXPECTED_TOOLS)


def test_mcp_has_instructions() -> None:
    assert "LennyVerse" in (mcp.instructions or "")
