"""CustomerSupportAgent — Kafka consumer for complaint events.

Listens on `telco.customers.complaints` topic.
When a ComplaintFiled event arrives, triggers the CustomerSupportAgent.
"""

from __future__ import annotations

import asyncio
import json
import logging

import structlog
from aiokafka import AIOKafkaConsumer

from agents.customer_support.agent import CustomerSupportAgentRunner
from shared.config.settings import get_settings

settings = get_settings()
logger = structlog.get_logger(__name__)

TOPIC = "telco.customers.complaints"
GROUP_ID = "customer-support-agent"


class ComplaintConsumer:
    """Kafka consumer that triggers the agent on complaint events."""

    def __init__(self) -> None:
        self._consumer: AIOKafkaConsumer | None = None
        self._agent_runner = CustomerSupportAgentRunner()
        self._running = False

    async def start(self) -> None:
        """Start consuming complaint events."""
        self._consumer = AIOKafkaConsumer(
            TOPIC,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=GROUP_ID,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="latest",
            enable_auto_commit=True,
        )
        await self._consumer.start()
        self._running = True
        logger.info("complaint_consumer_started", topic=TOPIC, group_id=GROUP_ID)

        try:
            async for msg in self._consumer:
                if not self._running:
                    break
                await self._handle_event(msg.value)
        finally:
            await self._consumer.stop()
            await self._agent_runner.close()
            logger.info("complaint_consumer_stopped")

    async def stop(self) -> None:
        """Gracefully stop the consumer."""
        self._running = False

    async def _handle_event(self, event: dict) -> None:
        """Process a single ComplaintFiled event."""
        try:
            logger.info(
                "complaint_event_received",
                event_type=event.get("event_type"),
                aggregate_id=event.get("aggregate_id"),
            )

            # Extract complaint data from the event payload
            customer_id = event.get("aggregate_id", "")
            complaint_type = event.get("complaint_type", "general")
            description = event.get("description", "No description provided")
            priority = event.get("priority", "medium")

            # Trigger the agent
            result = await self._agent_runner.handle_complaint(
                customer_id=customer_id,
                complaint_type=complaint_type,
                description=description,
                priority=priority,
            )

            logger.info(
                "complaint_handled",
                session_id=result["session_id"],
                customer_id=customer_id,
                complaint_type=complaint_type,
                message_count=result["message_count"],
            )

        except Exception:
            logger.exception("complaint_handling_failed", event=event)


async def run_consumer() -> None:
    """Entry point for running the consumer standalone."""
    consumer = ComplaintConsumer()
    try:
        await consumer.start()
    except asyncio.CancelledError:
        await consumer.stop()
