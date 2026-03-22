from __future__ import annotations

from fastapi import FastAPI

from backend.app.api.v1.galaxy import create_router
from backend.app.services.galaxy_query_service import GalaxyQueryService


def create_app(*, galaxy_service: GalaxyQueryService | None = None) -> FastAPI:
    app = FastAPI(title="LennyVerse API", version="0.1.0")
    app.include_router(create_router(service=galaxy_service), prefix="/api/v1")
    return app


app = create_app()
