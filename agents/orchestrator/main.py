"""Orchestrator — FastAPI entry point for the Supervisor Agent.

Endpoints:
  - GET  /health               — health check
  - POST /v1/orchestrator/route — manually trigger routing (for testing)
  - GET  /metrics              — Prometheus metrics endpoint

Background:
  - Kafka consumer listens on multiple topics and routes to specialists
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from langchain_core.messages import HumanMessage
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

consumer_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global consumer_task
    from agents.orchestrator.kafka_consumer import OrchestratorConsumer

    consumer = OrchestratorConsumer()
    consumer_task = asyncio.create_task(consumer.start())
    logger.info("orchestrator_service_started")
    yield
    await consumer.stop()
    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
    logger.info("orchestrator_service_stopped")


app = FastAPI(
    title="TelcoAgent Orchestrator",
    description="Supervisor agent that routes requests to specialist agents",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RouteRequest(BaseModel):
    customer_id: str = "unknown"
    message: str
    metadata: dict[str, Any] = {}


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "service": "orchestrator-agent"}


@app.post("/v1/orchestrator/route")
async def route_request(body: RouteRequest) -> dict[str, Any]:
    """Manually trigger the supervisor routing — bypasses Kafka."""
    from agents.orchestrator.supervisor import supervisor_graph

    initial_state = {
        "messages": [HumanMessage(content=body.message)],
        "customer_id": body.customer_id,
        "domain": "",
        "tools_used": [],
        "routing_decision": "",
        "final_response": None,
        "metadata": body.metadata,
    }

    result = await supervisor_graph.ainvoke(initial_state)

    return {
        "customer_id": body.customer_id,
        "domain": result.get("domain", "unknown"),
        "routing_decision": result.get("routing_decision", ""),
        "tools_used": result.get("tools_used", []),
        "final_response": result.get("final_response", ""),
    }


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> PlainTextResponse:
    return PlainTextResponse(
        content=generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )
