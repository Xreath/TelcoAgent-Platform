"""Customer Service — FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.customer.api.routes import router
from shared.config.settings import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup/shutdown tasks."""
    # Startup: create tables if they don't exist
    from shared.utils.database import Base, engine
    from services.customer.infrastructure.orm_models import ComplaintORM, CustomerORM  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Shutdown: close DB connections
    await engine.dispose()


app = FastAPI(
    title="Customer Service",
    description="TelcoAgent Platform — Customer Bounded Context",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "customer-service"}
