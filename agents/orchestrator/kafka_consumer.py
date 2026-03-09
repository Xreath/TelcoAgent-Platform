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

DLQ Strategy:
  - Deserialization/validation errors → DLQ immediately
  - Routing/processing errors → retry 3x with exponential backoff, then DLQ
"""

from __future__ import annotations

import asyncio
import json

import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from pydantic import BaseModel, ValidationError

from shared.config.settings import get_settings
from shared.kafka.retry import RetryConfig, RetryHandler
from shared.security import PromptInjectionError, sanitize_input

logger = structlog.get_logger(__name__)
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
        self._retry_handler: RetryHandler | None = None
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

        self._retry_handler = RetryHandler(
            config=RetryConfig(max_retries=3, base_delay_seconds=2.0, max_delay_seconds=30.0, dlq_topic=DLQ_TOPIC),
            dlq_producer=self._producer,
        )

        self._running = True
        logger.info("orchestrator_consumer_started", topics=CONSUME_TOPICS)

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
        assert self._retry_handler is not None

        try:
            data = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.exception("deserialization_error")
            await self._retry_handler.send_to_dlq(
                {"error": "deserialization_failed", "topic": topic},
                reason="deserialization_failed",
            )
            return

        try:
            event = AgentEvent(**data)
        except ValidationError as e:
            logger.warning("invalid_event", errors=e.errors())
            await self._retry_handler.send_to_dlq(
                {"error": "validation_failed", "event": data, "topic": topic},
                reason="validation_failed",
            )
            return

        await self._route_event(topic, event, data)

    async def _route_event(self, topic: str, event: AgentEvent, raw_data: dict) -> None:
        """Route event through the supervisor graph with retry logic."""
        from langchain_core.messages import HumanMessage

        assert self._retry_handler is not None

        domain_hint = TOPIC_TO_DOMAIN.get(topic, "customer_support")
        event_id = f"{event.aggregate_id}:{event.event_type}:{topic}"

        # Sanitize event description against prompt injection
        description = event.description or f"Event: {event.event_type}"
        try:
            description = sanitize_input(description, field_name="event_description")
        except PromptInjectionError as e:
            logger.error("prompt_injection_blocked", event_id=event_id, patterns=e.matched_patterns)
            assert self._retry_handler is not None
            await self._retry_handler.send_to_dlq(
                {**raw_data, "blocked_reason": "prompt_injection", "patterns": list(e.matched_patterns)},
                reason="prompt_injection_blocked",
            )
            return

        initial_state = {
            "messages": [HumanMessage(content=description)],
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

        while True:
            try:
                result = await self._graph.ainvoke(initial_state)

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
                    aggregate_id=event.aggregate_id,
                    domain=result.get("domain"),
                    routing_decision=result.get("routing_decision"),
                )
                self._retry_handler.clear_retry_state(event_id)
                return

            except Exception as exc:
                logger.exception("routing_failed", event_type=event.event_type)
                should_retry = await self._retry_handler.handle_retryable_error(
                    event_id=event_id,
                    event_data=raw_data,
                    error=exc,
                    source_topic=topic,
                )
                if not should_retry:
                    return


async def run_orchestrator() -> None:
    consumer = OrchestratorConsumer()
    try:
        await consumer.start()
    except asyncio.CancelledError:
        await consumer.stop()
