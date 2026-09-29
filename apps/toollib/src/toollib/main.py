from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import sessionmaker

from toollib.api import items, loans, members, testing
from toollib.clock import AppClock
from toollib.config import Settings
from toollib.db import Base, make_engine
from toollib.errors import DomainError


def create_app(settings: Settings | None = None, clock: AppClock | None = None) -> FastAPI:
    settings = settings or Settings()
    engine = make_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        Base.metadata.create_all(engine)
        yield
        engine.dispose()

    app = FastAPI(
        title="Tool Library",
        version="0.1.0",
        description="Members borrow tools, return them, and pay late fees. Rules: docs/domain.md.",
        lifespan=lifespan,
    )
    app.state.session_factory = sessionmaker(engine, expire_on_commit=False)
    app.state.clock = clock or AppClock()

    @app.exception_handler(DomainError)
    async def _domain_error(_request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.code, "message": exc.message}})

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        body = {"code": "VALIDATION_ERROR", "message": "Request is invalid", "details": exc.errors()}
        return JSONResponse(status_code=422, content=jsonable_encoder({"error": body}))

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(items.router)
    app.include_router(members.router)
    app.include_router(loans.router)
    if settings.test_mode:
        app.include_router(testing.router)

    return app


app = create_app()
