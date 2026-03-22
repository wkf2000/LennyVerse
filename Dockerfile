FROM node:22-slim AS frontend

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock README.md ./
COPY ingest/ ingest/
COPY backend/ backend/

RUN uv sync --frozen --no-dev --no-editable

FROM python:3.13-slim

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=frontend /app/frontend/dist /app/static

ENV PATH="/app/.venv/bin:$PATH"
ENV STATIC_ROOT=/app/static
ENV GALAXY_SNAPSHOT_DIR=/app/data/galaxy-snapshots

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
