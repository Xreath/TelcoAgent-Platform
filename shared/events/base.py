"""Base classes for Domain Events across all bounded contexts."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    """Base domain event — all events inherit from this."""

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    aggregate_id: str
    aggregate_type: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: int = 1

    model_config = {"frozen": True}
