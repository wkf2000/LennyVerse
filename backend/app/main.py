from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.v1.galaxy import create_router
from backend.app.services.galaxy_query_service import GalaxyQueryService


def _mount_static_and_spa(app: FastAPI, root: Path) -> None:
    assets = root / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    root_resolved = root.resolve()

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(root / "index.html")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse:
        if full_path.startswith("api"):
            raise HTTPException(status_code=404)
        candidate = (root / full_path).resolve()
        try:
            candidate.relative_to(root_resolved)
        except ValueError:
            return FileResponse(root / "index.html")
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(root / "index.html")


def create_app(*, galaxy_service: GalaxyQueryService | None = None) -> FastAPI:
    app = FastAPI(title="LennyVerse API", version="0.1.0")
    app.include_router(create_router(service=galaxy_service), prefix="/api/v1")

    static_root_raw = os.environ.get("STATIC_ROOT", "").strip()
    if static_root_raw:
        static_root = Path(static_root_raw)
        if static_root.is_dir():
            _mount_static_and_spa(app, static_root)

    return app


app = create_app()
