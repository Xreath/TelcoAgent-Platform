"""Campaign Domain — Value Objects."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import Field

from shared.models.base import ValueObject


class CampaignStatus(StrEnum):
    """Lifecycle status of a campaign."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class CampaignType(StrEnum):
    """Channel through which the campaign is delivered."""

    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"
    IN_APP = "in_app"


class TargetSegment(ValueObject):
    """References a customer segment for campaign targeting."""

    segment_name: str  # e.g. "platinum", "churning", "gold"
    min_clv: float | None = None
    max_clv: float | None = None
    region: str | None = None


class ABVariant(ValueObject):
    """A/B test variant with performance metrics."""

    variant_id: UUID = Field(default_factory=uuid4)
    content: str
    weight: float = 0.5  # traffic split weight (0.0 - 1.0)
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0

    model_config = {"frozen": False}  # override ValueObject frozen to allow metric updates

    @property
    def click_rate(self) -> float:
        """Click-through rate."""
        return self.clicks / self.impressions if self.impressions > 0 else 0.0

    @property
    def conversion_rate(self) -> float:
        """Conversion rate."""
        return self.conversions / self.impressions if self.impressions > 0 else 0.0
