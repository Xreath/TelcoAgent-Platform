"""Base classes for DDD building blocks — shared across all bounded contexts."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ValueObject(BaseModel):
    """Immutable value object — equality by value, not identity."""

    model_config = {"frozen": True}


class Entity(BaseModel):
    """Entity — has identity, mutable state."""

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AggregateRoot(Entity):
    """Aggregate Root — consistency boundary, collects domain events."""

    _domain_events: list = []

    def add_event(self, event: "DomainEvent") -> None:
        self._domain_events.append(event)

    def collect_events(self) -> list:
        events = self._domain_events.copy()
        self._domain_events.clear()
        return events

    @property
    def pending_events(self) -> list:
        return self._domain_events.copy()
