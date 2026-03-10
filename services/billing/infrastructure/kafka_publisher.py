"""Billing Service — Kafka event publisher via Outbox Pattern.

Same pattern as Customer Service — events saved to outbox.events table,
then polled and published to Kafka by OutboxPoller.
"""

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
                    (:id, :aggregate_type, :aggregate_id, :event_type, cast(:payload as jsonb))
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
    """Polls outbox table and publishes unpublished billing events to Kafka."""

    def __init__(self, kafka_bootstrap_servers: str) -> None:
        self._bootstrap_servers = kafka_bootstrap_servers
        self._topic_map = {
            "billing.invoice_created": "telco.billing.invoice_created",
            "billing.invoice_paid": "telco.billing.invoice_paid",
            "billing.anomaly_found": "telco.billing.anomaly_found",
            "billing.dispute_opened": "telco.billing.dispute_opened",
            "billing.dispute_resolved": "telco.billing.dispute_resolved",
            "billing.payment_failed": "telco.billing.payment_failed",
        }

    async def poll_and_publish(self) -> int:
        """Fetch unpublished events and send to Kafka. Returns count published."""
        from aiokafka import AIOKafkaProducer
        from sqlalchemy import text

        published_count = 0

        async with AsyncSessionFactory() as session:
            result = await session.execute(
                text("""
                    SELECT id, event_type, payload
                    FROM outbox.events
                    WHERE published = FALSE
                      AND aggregate_type IN ('Invoice', 'Dispute')
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
