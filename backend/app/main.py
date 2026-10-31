"""FirstRupee API entrypoint.

Start-up: runs Alembic migrations to head, then seeds the public Indian market catalogue (idempotent).
Errors: domain errors map to 4xx with a user-safe message; unexpected errors are logged server-side and return a generic 500.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app import __version__
from app.api.routes import analysis, auth, catalog, profile, schemes
from app.core.config import get_settings
from app.core.errors import DomainError
from app.db.migrate import database_startup_lock, run_migrations
from app.db.session import SessionLocal
from app.data_sources.provider import get_provider
from app.seed import seed_catalog
from app.services.financial_engine.rules import (
    EVALUATOR_VERSION,
    PASSPORT_SCHEMA_VERSION,
    PROMPT_VERSION,
    READINESS_RULE_VERSION,
    SIMULATOR_VERSION,
    TIMING_RULE_VERSION,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("firstrupee")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    with database_startup_lock():
        run_migrations()
        with SessionLocal() as session:
            seed_catalog(session)
    logger.info("FirstRupee API ready (schema at head, market catalogue present).")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="FirstRupee API", version=__version__, lifespan=lifespan,
                  docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )

    @app.exception_handler(DomainError)
    async def _domain_error(_request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message, "errors": exc.details})

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = []
        for item in exc.errors():
            field = ".".join(str(part) for part in item.get("loc", ()) if part not in ("body", "query", "path"))
            message = str(item.get("msg", "Invalid value")).removeprefix("Value error, ")
            errors.append({"field": field or "request", "message": message})
        return JSONResponse(status_code=422, content={"detail": "The submitted data failed validation.", "errors": errors})

    @app.exception_handler(Exception)
    async def _unexpected(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", type(exc).__name__)
        return JSONResponse(status_code=500, content={"detail": "Something went wrong. The incident has been logged."})

    for module in (auth, profile, analysis.readiness_router, catalog, analysis.timing_router, analysis.research_router,
                   analysis.simulator_router, analysis.passport_router, analysis.assistant_router, schemes.schemes_router):
        router = getattr(module, "router", module)
        app.include_router(router, prefix="/api")

    @app.get("/api/health", tags=["system"])
    def health() -> dict[str, object]:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        llm = settings.llm_enabled
        provider = get_provider()
        return {
            "ok": True,
            "service": "firstrupee-api",
            "version": __version__,
            "database": "ok",
            "rule_versions": {
                "readiness": READINESS_RULE_VERSION,
                "timing": TIMING_RULE_VERSION,
                "simulator": SIMULATOR_VERSION,
                "evaluator": EVALUATOR_VERSION,
                "prompts": PROMPT_VERSION,
                "passport": PASSPORT_SCHEMA_VERSION,
            },
            "language_model": {"enabled": llm, "provider": settings.llm_provider if llm else "none"},
            "market_data": {"provider": provider.id, "is_live": provider.is_live},
        }

    return app


app = create_app()
