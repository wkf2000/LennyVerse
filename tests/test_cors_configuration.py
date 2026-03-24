from __future__ import annotations

import importlib

from fastapi.middleware.cors import CORSMiddleware

import backend_api.config as config_module
import backend_api.main as main_module


def test_cors_middleware_not_enabled_without_origins(monkeypatch) -> None:
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)

    importlib.reload(config_module)
    importlib.reload(main_module)

    middleware_classes = [middleware.cls for middleware in main_module.app.user_middleware]

    assert CORSMiddleware not in middleware_classes
