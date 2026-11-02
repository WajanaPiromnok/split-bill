from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine

from splitbill.api import router
from splitbill.config import Settings
from splitbill.errors import install_error_handlers
from splitbill.expenses_api import router as expenses_router


def create_app(database_url: str | None = None) -> FastAPI:
    settings = Settings()
    engine = create_engine(
        database_url or settings.database_url,
        pool_pre_ping=True,
        isolation_level="READ COMMITTED",
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(
        title="SplitBill",
        version="0.1.0",
        description="SplitBill group access and shared expenses with exact monetary allocation.",
        lifespan=lifespan,
    )
    app.state.engine = engine
    install_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["X-User", "Idempotency-Key", "Content-Type"],
    )
    app.include_router(router)
    app.include_router(expenses_router)
    return app


app = create_app()
