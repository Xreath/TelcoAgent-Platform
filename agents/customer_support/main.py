"""CustomerSupportAgent — FastAPI application entry point.

Endpoints:
  - GET  /health              — health check
  - POST /v1/agent/complaint  — manually trigger agent (for testing)
  - GET  /metrics             — Prometheus metrics endpoint

Background:
  - Kafka consumer runs as a background task on startup
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel

from agents.customer_support.agent import CustomerSupportAgentRunner
from agents.customer_support.kafka_consumer import ComplaintConsumer

logger = structlog.get_logger(__name__)

# ── Lifespan ──────────────────────────────────────────────────

consumer = ComplaintConsumer()
consumer_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global consumer_task
    # Start Kafka consumer in background
    consumer_task = asyncio.create_task(consumer.start())
    logger.info("agent_service_started")
    yield
    # Shutdown
    await consumer.stop()
    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
    logger.info("agent_service_stopped")


# ── FastAPI app ───────────────────────────────────────────────

app = FastAPI(
    title="CustomerSupportAgent",
    description="TelcoAgent Platform — AI-powered customer support agent",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request schemas ───────────────────────────────────────────


class ComplaintRequest(BaseModel):
    customer_id: str
    complaint_type: str  # billing | network | service | general
    description: str
    priority: str = "medium"


# ── Endpoints ─────────────────────────────────────────────────


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "service": "customer-support-agent"}


@app.post("/v1/agent/complaint")
async def trigger_agent(body: ComplaintRequest) -> dict[str, Any]:
    """Manually trigger the agent for testing — bypasses Kafka."""
    runner = CustomerSupportAgentRunner()
    try:
        result = await runner.handle_complaint(
            customer_id=body.customer_id,
            complaint_type=body.complaint_type,
            description=body.description,
            priority=body.priority,
        )
        return result
    finally:
        await runner.close()


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> PlainTextResponse:
    """Expose Prometheus metrics."""
    return PlainTextResponse(
        content=generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )
