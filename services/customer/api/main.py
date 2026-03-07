"""Customer Service — FastAPI application entry point."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.customer.api.routes import router
from shared.config.settings import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run startup/shutdown tasks."""
    # Startup: create tables if they don't exist
    from services.customer.infrastructure.orm_models import ComplaintORM, CustomerORM  # noqa: F401
    from services.customer.infrastructure.kafka_publisher import OutboxPoller
    from shared.utils.database import Base, engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Background outbox poller: publishes domain events to Kafka every 5s
    poller = OutboxPoller(settings.kafka_bootstrap_servers)

    async def poll_loop() -> None:
        while True:
            await asyncio.sleep(5)
            try:
                await poller.poll_and_publish()
            except Exception:
                pass

    poll_task = asyncio.create_task(poll_loop())

    yield

    poll_task.cancel()
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
async def health() -> dict[str, Any]:
    return {"status": "ok", "service": "customer-service"}
