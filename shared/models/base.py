"""Base classes for DDD building blocks — shared across all bounded contexts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, PrivateAttr

if TYPE_CHECKING:
    from shared.events.base import DomainEvent


class ValueObject(BaseModel):
    """Immutable value object — equality by value, not identity."""

    model_config = {"frozen": True}


class Entity(BaseModel):
    """Entity — has identity, mutable state."""

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AggregateRoot(Entity):
    """Aggregate Root — consistency boundary, collects domain events."""

    _domain_events: list[DomainEvent] = PrivateAttr(default_factory=list)

    def add_event(self, event: DomainEvent) -> None:
        self._domain_events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        events = self._domain_events.copy()
        self._domain_events.clear()
        return events

    @property
    def pending_events(self) -> list[DomainEvent]:
        return self._domain_events.copy()
