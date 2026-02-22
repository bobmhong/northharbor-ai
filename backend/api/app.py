"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.analytics.router import router as analytics_router
from backend.api.deps import init_stores
from backend.api.middleware import RequestLoggingMiddleware
from backend.config import get_settings
from backend.interview.router import router as interview_router
from backend.pipelines.router import router as pipelines_router
from backend.security.headers import SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    await init_stores(settings)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="NorthHarbor Sage",
        description="AI-powered retirement planning assistant",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(interview_router)
    app.include_router(pipelines_router)
    app.include_router(analytics_router)

    @app.get("/api/health")
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "store_backend": get_settings().store_backend}

    return app
