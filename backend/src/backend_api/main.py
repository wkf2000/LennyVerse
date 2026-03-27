from __future__ import annotations

import logging
import sys
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from backend_api.config import Settings, get_settings
from backend_api.generate_schemas import ExecuteRequest, OutlineRequest, OutlineResponse
from backend_api.generate_service import GenerateService
from backend_api.llm_client import ChatCompletionStreamer, OpenAiCompatibleChatStreamer
from backend_api.graph_repository import GraphRepository
from backend_api.graph_service import GraphFilters, GraphService
from backend_api.rag_repository import RagRepository
from backend_api.rag_schemas import ChatRequest, SearchRequest, SearchResponse
from backend_api.rag_service import (
    RagFilterValidationError,
    RagRetrievalTimeoutError,
    RagService,
    format_sse_event,
    validate_rag_filters,
)
from backend_api.schemas import GraphResponse, NodeDetailResponse, NodeType
from backend_api.stats_repository import StatsRepository
from backend_api.stats_schemas import TopicTrendsResponse
from backend_api.stats_service import StatsService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("lennyverse")

logger.info("Starting LennyVerse API v0.2.0")

app = FastAPI(title="LennyVerse API", version="0.2.0")
settings = get_settings()

logger.info("Configuration loaded")
logger.info("  Database URL: %s", "configured" if settings.supabase_db_url else "NOT SET")
logger.info("  OpenAI API base: %s", settings.openai_api_base or "not configured")
logger.info("  OpenAI model: %s", settings.openai_model)
logger.info("  Embedding model: %s", settings.embedding_model)
logger.info("  Embedding base URL: %s", settings.ollama_embed_base_url)
logger.info("  RAG default k: %d, max k: %d", settings.rag_default_k, settings.rag_max_k)
logger.info("  RAG retrieval timeout: %ds, chat timeout: %ds",
            settings.rag_retrieval_timeout_seconds, settings.rag_chat_timeout_seconds)
logger.info("  Generate max weeks: %d, outline k: %d, timeout: %ds",
            settings.generate_max_weeks, settings.generate_outline_k, settings.generate_timeout_seconds)

if settings.cors_allow_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("CORS middleware enabled for origins: %s", settings.cors_allow_origins)
else:
    logger.info("CORS middleware not configured (no origins specified)")


def get_graph_repository(
    app_settings: Annotated[Settings, Depends(get_settings)],
) -> GraphRepository:
    return GraphRepository(app_settings.require_db_url())


def get_graph_service(
    repository: Annotated[GraphRepository, Depends(get_graph_repository)],
) -> GraphService:
    return GraphService(repository)


def get_rag_repository(
    app_settings: Annotated[Settings, Depends(get_settings)],
) -> RagRepository:
    return RagRepository(
        app_settings.require_db_url(),
        timeout_seconds=app_settings.rag_retrieval_timeout_seconds,
    )


def get_rag_service(
    repository: Annotated[RagRepository, Depends(get_rag_repository)],
    app_settings: Annotated[Settings, Depends(get_settings)],
) -> RagService:
    return RagService(repository=repository, settings=app_settings)


def get_llm_client(app_settings: Annotated[Settings, Depends(get_settings)]) -> ChatCompletionStreamer:
    try:
        return OpenAiCompatibleChatStreamer(app_settings)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def get_generate_service(
    repository: Annotated[RagRepository, Depends(get_rag_repository)],
    app_settings: Annotated[Settings, Depends(get_settings)],
) -> GenerateService:
    return GenerateService(repository=repository, settings=app_settings)


def get_stats_repository(
    app_settings: Annotated[Settings, Depends(get_settings)],
) -> StatsRepository:
    return StatsRepository(app_settings.require_db_url())


def get_stats_service(
    repository: Annotated[StatsRepository, Depends(get_stats_repository)],
) -> StatsService:
    return StatsService(repository)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/graph", response_model=GraphResponse)
def get_graph(
    service: Annotated[GraphService, Depends(get_graph_service)],
    node_types: Annotated[list[NodeType] | None, Query(alias="nodeType")] = None,
    topic: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> GraphResponse:
    filters = GraphFilters(
        node_types=set(node_types) if node_types else None,
        topic=topic.strip() if topic else None,
        start_date=start_date,
        end_date=end_date,
    )
    return service.get_graph(filters)


@app.get("/api/graph/nodes/{node_id}", response_model=NodeDetailResponse)
def get_graph_node(
    node_id: str,
    service: Annotated[GraphService, Depends(get_graph_service)],
) -> NodeDetailResponse:
    detail = service.get_node_detail(node_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found.")
    return detail


@app.post("/api/search", response_model=SearchResponse)
def post_search(
    body: SearchRequest,
    service: Annotated[RagService, Depends(get_rag_service)],
) -> SearchResponse:
    try:
        return service.search(body.query, k=body.k, filters=body.filters)
    except RagFilterValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RagRetrievalTimeoutError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/chat")
def post_chat(
    body: ChatRequest,
    service: Annotated[RagService, Depends(get_rag_service)],
    app_settings: Annotated[Settings, Depends(get_settings)],
    llm: Annotated[ChatCompletionStreamer, Depends(get_llm_client)],
) -> StreamingResponse:
    stripped = body.query.strip()
    if not stripped:
        raise HTTPException(
            status_code=422,
            detail="query must not be empty or whitespace only",
        )
    try:
        validate_rag_filters(body.filters)
    except RagFilterValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    normalized = body.model_copy(update={"query": stripped})

    def event_stream() -> Iterator[str]:
        yield from service.iter_chat_sse_lines(
            normalized,
            llm=llm,
            chat_timeout_seconds=app_settings.rag_chat_timeout_seconds,
            model=app_settings.openai_model,
        )

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/generate/outline", response_model=OutlineResponse)
def post_generate_outline(
    body: OutlineRequest,
    service: Annotated[GenerateService, Depends(get_generate_service)],
) -> OutlineResponse:
    return service.generate_outline(
        topic=body.topic,
        num_weeks=body.num_weeks,
        difficulty=body.difficulty,
    )


@app.post("/api/generate/execute")
def post_generate_execute(
    body: ExecuteRequest,
    service: Annotated[GenerateService, Depends(get_generate_service)],
) -> StreamingResponse:
    def event_stream() -> Iterator[str]:
        for event_name, payload in service.iter_generate_sse_events(
            topic=body.topic,
            num_weeks=body.num_weeks,
            difficulty=body.difficulty,
            approved_outline=body.approved_outline,
        ):
            yield format_sse_event(event_name, payload)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/stats/topic-trends", response_model=TopicTrendsResponse)
def get_topic_trends(
    service: Annotated[StatsService, Depends(get_stats_service)],
) -> TopicTrendsResponse:
    return service.get_topic_trends()


_FRONTEND_DIST_DIR = Path(__file__).resolve().parents[3] / "frontend" / "dist"
_FRONTEND_INDEX_FILE = _FRONTEND_DIST_DIR / "index.html"
_RESERVED_NON_SPA_PREFIXES = {"api", "docs", "redoc", "openapi.json", "health"}

logger.info("Registered API routes: %s", [r.path for r in app.routes if hasattr(r, "path")])

if _FRONTEND_DIST_DIR.exists() and _FRONTEND_INDEX_FILE.exists():
    logger.info("Frontend dist found at %s — enabling SPA serving", _FRONTEND_DIST_DIR)
    assets_dir = _FRONTEND_DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
        logger.info("Mounted /assets static files directory")

    @app.get("/", include_in_schema=False)
    def serve_frontend_root() -> FileResponse:
        return FileResponse(_FRONTEND_INDEX_FILE)

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend_spa(full_path: str) -> FileResponse:
        if full_path.split("/", 1)[0] in _RESERVED_NON_SPA_PREFIXES:
            raise HTTPException(status_code=404, detail="Not found.")

        requested_file = _FRONTEND_DIST_DIR / full_path
        if requested_file.is_file():
            return FileResponse(requested_file)

        return FileResponse(_FRONTEND_INDEX_FILE)
else:
    logger.warning("Frontend dist not found at %s — SPA serving disabled", _FRONTEND_DIST_DIR)

logger.info("LennyVerse API startup complete")
