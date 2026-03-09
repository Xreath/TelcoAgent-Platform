"""CustomerSupportAgent — Kafka consumer for complaint events.

Listens on `telco.customers.complaints` topic.
When a ComplaintFiled event arrives, triggers the CustomerSupportAgent.

DLQ Strategy:
  - Deserialization/validation errors → DLQ immediately (not retryable)
  - Processing errors → retry 3x with exponential backoff, then DLQ
"""

from __future__ import annotations

import asyncio
import json

import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from pydantic import BaseModel, ValidationError

from agents.customer_support.agent import CustomerSupportAgentRunner
from agents.customer_support.metrics import AgentMetrics
from shared.config.settings import get_settings
from shared.kafka.retry import RetryConfig, RetryHandler

settings = get_settings()
logger = structlog.get_logger(__name__)

TOPIC = "telco.customers.complaints"
DLQ_TOPIC = "telco.dlq.complaints"
GROUP_ID = "customer-support-agent"


class ComplaintEvent(BaseModel):
    """Schema for incoming complaint events."""

    aggregate_id: str
    event_type: str = "customer.complaint_filed"
    complaint_type: str = "general"
    description: str = "No description provided"
    priority: str = "medium"


def _safe_deserialize(raw: bytes) -> dict | None:
    """Safely deserialize a Kafka message, returning None on failure."""
    try:
        return json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.exception("deserialization_error", raw_hex=raw[:100].hex())
        return None


class ComplaintConsumer:
    """Kafka consumer that triggers the agent on complaint events."""

    def __init__(self) -> None:
        self._consumer: AIOKafkaConsumer | None = None
        self._dlq_producer: AIOKafkaProducer | None = None
        self._agent_runner = CustomerSupportAgentRunner()
        self._metrics = AgentMetrics()
        self._retry_handler: RetryHandler | None = None
        self._running = False

    async def start(self) -> None:
        """Start consuming complaint events."""
        self._consumer = AIOKafkaConsumer(
            TOPIC,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=GROUP_ID,
            value_deserializer=lambda v: v,  # raw bytes, we deserialize manually
            auto_offset_reset="latest",
            enable_auto_commit=True,
        )
        self._dlq_producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        )
        await self._consumer.start()
        await self._dlq_producer.start()

        self._retry_handler = RetryHandler(
            config=RetryConfig(max_retries=3, base_delay_seconds=2.0, max_delay_seconds=30.0, dlq_topic=DLQ_TOPIC),
            dlq_producer=self._dlq_producer,
        )

        self._running = True
        logger.info("complaint_consumer_started", topic=TOPIC, group_id=GROUP_ID)

        try:
            async for msg in self._consumer:
                if not self._running:
                    break
                await self._handle_message(msg.value)
        finally:
            await self._consumer.stop()
            await self._dlq_producer.stop()
            await self._agent_runner.close()
            logger.info("complaint_consumer_stopped")

    async def stop(self) -> None:
        """Gracefully stop the consumer."""
        self._running = False

    async def _handle_message(self, raw: bytes) -> None:
        """Deserialize and process a single message."""
        assert self._retry_handler is not None

        data = _safe_deserialize(raw)
        if data is None:
            await self._retry_handler.send_to_dlq(
                {"error": "deserialization_failed", "raw_hex": raw[:200].hex()},
                reason="deserialization_failed",
            )
            self._metrics.track_error("deserialization")
            return

        await self._handle_event(data)

    async def _handle_event(self, event: dict) -> None:
        """Process a single ComplaintFiled event with retry logic."""
        assert self._retry_handler is not None

        try:
            validated = ComplaintEvent(**event)
        except ValidationError as e:
            logger.warning("invalid_event_schema", errors=e.errors(), event=event)
            await self._retry_handler.send_to_dlq(
                {"error": "validation_failed", "details": e.errors(), "event": event},
                reason="validation_failed",
            )
            self._metrics.track_error("validation")
            return

        event_id = f"{validated.aggregate_id}:{validated.event_type}"

        while True:
            try:
                logger.info(
                    "complaint_event_received",
                    event_type=validated.event_type,
                    aggregate_id=validated.aggregate_id,
                )

                result = await self._agent_runner.handle_complaint(
                    customer_id=validated.aggregate_id,
                    complaint_type=validated.complaint_type,
                    description=validated.description,
                    priority=validated.priority,
                )

                logger.info(
                    "complaint_handled",
                    session_id=result["session_id"],
                    customer_id=validated.aggregate_id,
                    complaint_type=validated.complaint_type,
                    message_count=result["message_count"],
                )
                self._retry_handler.clear_retry_state(event_id)
                return

            except Exception as exc:
                logger.exception("complaint_handling_failed", event=event)
                self._metrics.track_error("processing")
                should_retry = await self._retry_handler.handle_retryable_error(
                    event_id=event_id,
                    event_data=event,
                    error=exc,
                    source_topic=TOPIC,
                )
                if not should_retry:
                    return
                # Loop continues for retry


async def run_consumer() -> None:
    """Entry point for running the consumer standalone."""
    consumer = ComplaintConsumer()
    try:
        await consumer.start()
    except asyncio.CancelledError:
        await consumer.stop()
