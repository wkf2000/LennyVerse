FROM python:3.13-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml README.md ./
COPY backend ./backend
COPY data-pipeline ./data-pipeline
COPY data ./data

RUN uv sync --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/backend/src:/app/data-pipeline/src"

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "backend_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
