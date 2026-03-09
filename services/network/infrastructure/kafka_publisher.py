"""Network Service — Kafka event publisher via Outbox Pattern.

Outbox Pattern:
  1. Domain event -> saved to outbox.events table (same DB transaction as business data)
  2. A separate poller reads unpublished events and sends them to Kafka
  3. Marks events as published after successful Kafka delivery

This guarantees atomicity — no event is lost even if the service crashes.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from shared.events.base import DomainEvent
from shared.utils.database import AsyncSessionFactory


class OutboxRepository:
    """Saves domain events to the outbox table within the same transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, event: DomainEvent) -> None:
        from sqlalchemy import text

        await self._session.execute(
            text("""
                INSERT INTO outbox.events
                    (id, aggregate_type, aggregate_id, event_type, payload)
                VALUES
                    (:id, :aggregate_type, :aggregate_id, :event_type, :payload::jsonb)
            """),
            {
                "id": str(uuid.uuid4()),
                "aggregate_type": event.aggregate_type,
                "aggregate_id": event.aggregate_id,
                "event_type": event.event_type,
                "payload": json.dumps(event.model_dump(), default=str),
            },
        )
        await self._session.flush()


class OutboxPoller:
    """Polls outbox table and publishes unpublished events to Kafka.

    In production this would run as a separate process or scheduled task.
    For dev/learning purposes it runs inline after each transaction.
    """

    def __init__(self, kafka_bootstrap_servers: str) -> None:
        self._bootstrap_servers = kafka_bootstrap_servers
        self._topic_map = {
            "network.node_created": "telco.network.node_created",
            "network.node_status_changed": "telco.network.status_changed",
            "network.anomaly_detected": "telco.network.anomalies",
            "network.fault_resolved": "telco.network.fault_resolved",
            "network.capacity_threshold_reached": "telco.network.capacity_warnings",
        }

    async def poll_and_publish(self) -> int:
        """Fetch unpublished events and send to Kafka. Returns count published."""
        from aiokafka import AIOKafkaProducer
        from sqlalchemy import text

        published_count = 0

        async with AsyncSessionFactory() as session:
            # Fetch unpublished events (limit 100 per poll)
            result = await session.execute(
                text("""
                    SELECT id, event_type, payload
                    FROM outbox.events
                    WHERE published = FALSE
                      AND aggregate_type = 'NetworkNode'
                    ORDER BY created_at
                    LIMIT 100
                """)
            )
            events = result.fetchall()

            if not events:
                return 0

            producer = AIOKafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            await producer.start()

            try:
                for event_id, event_type, payload in events:
                    topic = self._topic_map.get(event_type, "telco.agents.decisions")
                    await producer.send_and_wait(topic, value=payload)

                    # Mark as published
                    await session.execute(
                        text("""
                            UPDATE outbox.events
                            SET published = TRUE, published_at = :now
                            WHERE id = :id
                        """),
                        {"id": event_id, "now": datetime.now(UTC)},
                    )
                    published_count += 1

                await session.commit()
            finally:
                await producer.stop()

        return published_count
