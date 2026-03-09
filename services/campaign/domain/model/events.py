"""Campaign Domain — Domain Events."""

from __future__ import annotations

from shared.events.base import DomainEvent


class CampaignGenerated(DomainEvent):
    """Raised when a new campaign is created."""

    event_type: str = "campaign.generated"
    aggregate_type: str = "Campaign"
    name: str
    campaign_type: str
    target_segment: str


class ABVariantSelected(DomainEvent):
    """Raised when an A/B variant is added to a campaign."""

    event_type: str = "campaign.ab_variant_selected"
    aggregate_type: str = "Campaign"
    variant_id: str
    content: str
    weight: float


class CampaignDelivered(DomainEvent):
    """Raised when a campaign transitions to completed status."""

    event_type: str = "campaign.delivered"
    aggregate_type: str = "Campaign"
    campaign_type: str
    target_segment: str
    total_variants: int
