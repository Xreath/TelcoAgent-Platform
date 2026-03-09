"""Orchestrator — Kafka consumer for multi-topic agent routing.

Listens on multiple topics and routes events to the supervisor agent.
Also publishes agent decisions to telco.agents.decisions topic.

Topics consumed:
  - telco.customers.complaints → CustomerSupportAgent
  - telco.billing.anomalies → BillingAnalystAgent
  - telco.network.anomalies → NetworkDiagnosticAgent
  - telco.campaigns.requests → CampaignAgent

Topic produced:
  - telco.agents.decisions — every agent decision is logged here
"""

from __future__ import annotations

import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from pydantic import BaseModel, ValidationError

from shared.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

CONSUME_TOPICS = [
    "telco.customers.complaints",
    "telco.billing.anomalies",
    "telco.network.anomalies",
    "telco.campaigns.requests",
]
DECISION_TOPIC = "telco.agents.decisions"
DLQ_TOPIC = "telco.dlq.orchestrator"
GROUP_ID = "orchestrator-agent"


class AgentEvent(BaseModel):
    """Unified event schema for all incoming agent events."""

    aggregate_id: str
    event_type: str
    description: str = ""
    priority: str = "medium"
    metadata: dict = {}


TOPIC_TO_DOMAIN = {
    "telco.customers.complaints": "customer_support",
    "telco.billing.anomalies": "billing",
    "telco.network.anomalies": "network",
    "telco.campaigns.requests": "campaign",
}


class OrchestratorConsumer:
    """Kafka consumer that routes events to the supervisor graph."""

    def __init__(self) -> None:
        self._consumer: AIOKafkaConsumer | None = None
        self._producer: AIOKafkaProducer | None = None
        self._running = False

    async def start(self) -> None:
        from agents.orchestrator.supervisor import supervisor_graph

        self._graph = supervisor_graph
        self._consumer = AIOKafkaConsumer(
            *CONSUME_TOPICS,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=GROUP_ID,
            value_deserializer=lambda v: v,
            auto_offset_reset="latest",
            enable_auto_commit=True,
        )
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        )
        await self._consumer.start()
        await self._producer.start()
        self._running = True
        logger.info("orchestrator_consumer_started", extra={"topics": CONSUME_TOPICS})

        try:
            async for msg in self._consumer:
                if not self._running:
                    break
                await self._handle_message(msg.topic, msg.value)
        finally:
            await self._consumer.stop()
            await self._producer.stop()

    async def stop(self) -> None:
        self._running = False

    async def _handle_message(self, topic: str, raw: bytes) -> None:
        try:
            data = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.exception("deserialization_error")
            await self._send_to_dlq({"error": "deserialization_failed", "topic": topic})
            return

        try:
            event = AgentEvent(**data)
        except ValidationError as e:
            logger.warning("invalid_event", extra={"errors": e.errors()})
            await self._send_to_dlq({"error": "validation_failed", "event": data, "topic": topic})
            return

        await self._route_event(topic, event)

    async def _route_event(self, topic: str, event: AgentEvent) -> None:
        """Route event through the supervisor graph."""
        from langchain_core.messages import HumanMessage

        domain_hint = TOPIC_TO_DOMAIN.get(topic, "customer_support")

        initial_state = {
            "messages": [HumanMessage(content=event.description or f"Event: {event.event_type}")],
            "customer_id": event.aggregate_id,
            "domain": "",
            "tools_used": [],
            "routing_decision": "",
            "final_response": None,
            "metadata": {
                "source_topic": topic,
                "event_type": event.event_type,
                "priority": event.priority,
                "domain_hint": domain_hint,
                **event.metadata,
            },
        }

        try:
            result = await self._graph.ainvoke(initial_state)

            # Publish decision event
            decision = {
                "aggregate_id": event.aggregate_id,
                "event_type": "agent.decision.made",
                "source_topic": topic,
                "domain": result.get("domain", domain_hint),
                "routing_decision": result.get("routing_decision", ""),
                "tools_used": result.get("tools_used", []),
                "response_length": len(result.get("final_response", "") or ""),
            }
            if self._producer:
                await self._producer.send_and_wait(DECISION_TOPIC, value=decision)

            logger.info(
                "event_routed",
                extra={
                    "aggregate_id": event.aggregate_id,
                    "domain": result.get("domain"),
                    "routing_decision": result.get("routing_decision"),
                },
            )
        except Exception:
            logger.exception("routing_failed", extra={"event_type": event.event_type})
            await self._send_to_dlq({"error": "routing_failed", "topic": topic, "event_type": event.event_type})

    async def _send_to_dlq(self, payload: dict) -> None:
        if self._producer:
            try:
                await self._producer.send_and_wait(DLQ_TOPIC, value=payload)
            except Exception:
                logger.exception("dlq_send_failed")


async def run_orchestrator() -> None:
    consumer = OrchestratorConsumer()
    try:
        await consumer.start()
    except asyncio.CancelledError:
        await consumer.stop()
