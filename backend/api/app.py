"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.analytics.router import router as analytics_router
from backend.api.middleware import RequestLoggingMiddleware
from backend.interview.router import router as interview_router
from backend.pipelines.router import router as pipelines_router
from backend.security.headers import SecurityHeadersMiddleware


def create_app() -> FastAPI:
    app = FastAPI(
        title="North Harbor AI",
        description="AI-powered retirement planning assistant",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
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
        return {"status": "ok"}

    return app
