PYTHONPATH := backend/src:data-pipeline/src

.PHONY: setup run-api ingest ingest-dry-run migrate verify test normalize-data summarize

setup:
	uv sync

run-api:
	PYTHONPATH=$(PYTHONPATH) uv run uvicorn backend_api.main:app --host 0.0.0.0 --port 8000 --reload

normalize-data:
	PYTHONPATH=$(PYTHONPATH) uv run python -m data_pipeline.scripts.normalize_dataset

ingest:
	PYTHONPATH=$(PYTHONPATH) uv run python -m data_pipeline.scripts.ingest

ingest-limit:
	PYTHONPATH=$(PYTHONPATH) uv run python -m data_pipeline.scripts.ingest --limit $(LIMIT)

ingest-dry-run:
	PYTHONPATH=$(PYTHONPATH) uv run python -m data_pipeline.scripts.ingest --dry-run

ingest-dry-run-limit:
	PYTHONPATH=$(PYTHONPATH) uv run python -m data_pipeline.scripts.ingest --dry-run --limit $(LIMIT)

migrate:
	PYTHONPATH=$(PYTHONPATH) uv run python -m data_pipeline.scripts.apply_migrations

verify:
	PYTHONPATH=$(PYTHONPATH) uv run python -m data_pipeline.scripts.verify_ingest

summarize:
	PYTHONPATH=$(PYTHONPATH) uv run python -m data_pipeline.scripts.summarize

test:
	PYTHONPATH=$(PYTHONPATH) uv run pytest
