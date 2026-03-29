#!/bin/sh
set -e

# MCP server talks to FastAPI at localhost inside the container
export LENNYVERSE_API_BASE="http://localhost:8000"

# Start the MCP server in the background (SSE transport on port 8001)
uv run python -m backend_api.mcp_server --sse --port 8001 &

# Start FastAPI in the foreground
exec uv run uvicorn backend_api.main:app --host 0.0.0.0 --port 8000
