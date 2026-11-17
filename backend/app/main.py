from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.config import Settings
from app.core.db import make_engine
from app.middleware.audit import audit_writes
from app.routers import cases, deadlines, documents, graph, law, notices, plan
from app.services.llm import OllamaProvider


def create_app(settings: Settings | None = None) -> FastAPI:
    options = settings or Settings()
    engine = make_engine(options.database_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        engine.dispose()

    app = FastAPI(
        title="Investigation Copilot",
        description="Synthetic financial-fraud training workspace.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = options
    app.state.engine = engine
    app.state.llm = OllamaProvider(options)

    @app.middleware("http")
    async def response_headers(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    app.middleware("http")(audit_writes)
    app.add_middleware(
        CORSMiddleware, allow_origins=[options.allowed_origin],
        allow_methods=["GET", "POST", "PATCH"], allow_headers=["Authorization", "Content-Type", "X-Filename"],
    )

    @app.exception_handler(IntegrityError)
    async def handle_conflict(_request: Request, _error: IntegrityError):
        return JSONResponse(status_code=409, content={"detail": "The record conflicts with an existing entry"})

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_request: Request, exc: RequestValidationError):
        errors = [
            {"field": ".".join(str(segment) for segment in item["loc"]), "message": item["msg"]}
            for item in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": errors})

    @app.get("/health")
    def health():
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return JSONResponse(status_code=503, content={"status": "unavailable"})
        return {"status": "ok", "mode": "synthetic-demo"}

    for router in (cases, documents, law, plan, notices, graph, deadlines):
        app.include_router(router.router, prefix="/api")

    return app


app = create_app()
