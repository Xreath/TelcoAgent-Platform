"""Kafka consumer retry handler with exponential backoff and DLQ.

Strategy:
  1. On processing failure, retry up to `max_retries` times with exponential backoff.
  2. Backoff: base_delay * 2^attempt (capped at max_delay).
  3. After exhausting retries, send to DLQ with full error context.
  4. Deserialization and validation errors go directly to DLQ (not retryable).
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field

import structlog
from aiokafka import AIOKafkaProducer

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    dlq_topic: str = "telco.dlq.default"


@dataclass
class RetryRecord:
    """Tracks retry state for a single event."""

    attempt: int = 0
    first_failure_at: float = field(default_factory=time.time)
    last_error: str = ""


class RetryHandler:
    """Handles retry logic with exponential backoff before dead-lettering.

    Usage:
        handler = RetryHandler(config, dlq_producer)

        # For retryable errors (processing failures):
        should_retry = await handler.handle_retryable_error(event_id, event_data, error)
        if should_retry:
            # re-process the event
        # else: already sent to DLQ

        # For non-retryable errors (deserialization, validation):
        await handler.send_to_dlq(payload, reason="validation_failed")
    """

    def __init__(self, config: RetryConfig, dlq_producer: AIOKafkaProducer | None) -> None:
        self._config = config
        self._dlq_producer = dlq_producer
        self._retry_state: dict[str, RetryRecord] = {}

    @property
    def config(self) -> RetryConfig:
        return self._config

    async def handle_retryable_error(
        self,
        event_id: str,
        event_data: dict,
        error: Exception,
        source_topic: str = "",
    ) -> bool:
        """Handle a retryable processing error.

        Returns True if the event should be retried, False if sent to DLQ.
        """
        record = self._retry_state.get(event_id, RetryRecord())
        record.attempt += 1
        record.last_error = f"{type(error).__name__}: {error}"
        self._retry_state[event_id] = record

        if record.attempt <= self._config.max_retries:
            delay = self._calculate_delay(record.attempt)
            logger.warning(
                "retry_scheduled",
                event_id=event_id,
                attempt=record.attempt,
                max_retries=self._config.max_retries,
                delay_seconds=delay,
                error=record.last_error,
            )
            await asyncio.sleep(delay)
            return True

        # Exhausted retries — send to DLQ
        await self.send_to_dlq(
            payload={
                "error": "max_retries_exhausted",
                "event": event_data,
                "source_topic": source_topic,
                "attempts": record.attempt,
                "first_failure_at": record.first_failure_at,
                "last_error": record.last_error,
            },
            reason="max_retries_exhausted",
        )
        self._retry_state.pop(event_id, None)
        return False

    def clear_retry_state(self, event_id: str) -> None:
        """Clear retry state after successful processing."""
        self._retry_state.pop(event_id, None)

    async def send_to_dlq(self, payload: dict, reason: str = "unknown") -> None:
        """Send a failed message to the Dead Letter Queue."""
        if not self._dlq_producer:
            logger.error("dlq_producer_not_available", reason=reason)
            return

        enriched = {
            **payload,
            "dlq_reason": reason,
            "dlq_topic": self._config.dlq_topic,
            "dlq_timestamp": time.time(),
        }

        try:
            await self._dlq_producer.send_and_wait(
                self._config.dlq_topic,
                value=json.dumps(enriched, default=str).encode("utf-8"),
            )
            logger.info("sent_to_dlq", topic=self._config.dlq_topic, reason=reason)
        except Exception:
            logger.exception("dlq_send_failed", topic=self._config.dlq_topic)

    def _calculate_delay(self, attempt: int) -> float:
        """Exponential backoff: base * 2^(attempt-1), capped at max."""
        delay = self._config.base_delay_seconds * (2 ** (attempt - 1))
        return min(delay, self._config.max_delay_seconds)
