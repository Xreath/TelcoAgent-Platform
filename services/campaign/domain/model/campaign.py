"""Campaign Domain — Aggregate Root."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import Field

from services.campaign.domain.model.events import (
    ABVariantSelected,
    CampaignDelivered,
    CampaignGenerated,
)
from services.campaign.domain.model.value_objects import (
    ABVariant,
    CampaignStatus,
    CampaignType,
)
from shared.models.base import AggregateRoot


class Campaign(AggregateRoot):
    """Campaign Aggregate Root — consistency boundary for campaign data."""

    name: str
    campaign_type: CampaignType
    target_segment: str
    status: CampaignStatus = CampaignStatus.DRAFT
    content_template: str = ""
    variants: list[ABVariant] = Field(default_factory=list)

    @classmethod
    def create(
        cls,
        name: str,
        campaign_type: CampaignType,
        target_segment: str,
        content_template: str = "",
    ) -> Campaign:
        """Factory method — creates campaign and raises CampaignGenerated event."""
        campaign = cls(
            name=name,
            campaign_type=campaign_type,
            target_segment=target_segment,
            content_template=content_template,
        )
        campaign.add_event(
            CampaignGenerated(
                aggregate_id=str(campaign.id),
                name=name,
                campaign_type=campaign_type.value,
                target_segment=target_segment,
            )
        )
        return campaign

    def update_status(self, new_status: CampaignStatus) -> None:
        """Transition campaign status with validation."""
        allowed_transitions: dict[CampaignStatus, set[CampaignStatus]] = {
            CampaignStatus.DRAFT: {CampaignStatus.ACTIVE, CampaignStatus.ARCHIVED},
            CampaignStatus.ACTIVE: {CampaignStatus.PAUSED, CampaignStatus.COMPLETED},
            CampaignStatus.PAUSED: {CampaignStatus.ACTIVE, CampaignStatus.COMPLETED, CampaignStatus.ARCHIVED},
            CampaignStatus.COMPLETED: {CampaignStatus.ARCHIVED},
            CampaignStatus.ARCHIVED: set(),
        }

        if new_status not in allowed_transitions.get(self.status, set()):
            raise ValueError(f"Cannot transition from {self.status} to {new_status}")

        self.status = new_status
        self.updated_at = datetime.now(UTC)

        if new_status == CampaignStatus.COMPLETED:
            self.add_event(
                CampaignDelivered(
                    aggregate_id=str(self.id),
                    campaign_type=self.campaign_type.value,
                    target_segment=self.target_segment,
                    total_variants=len(self.variants),
                )
            )

    def add_variant(self, content: str, weight: float = 0.5) -> ABVariant:
        """Add an A/B variant to the campaign."""
        variant = ABVariant(content=content, weight=weight)
        self.variants.append(variant)
        self.updated_at = datetime.now(UTC)

        self.add_event(
            ABVariantSelected(
                aggregate_id=str(self.id),
                variant_id=str(variant.variant_id),
                content=content,
                weight=weight,
            )
        )
        return variant

    def generate_content(self, generated_text: str) -> None:
        """Set LLM-generated campaign content (mock in domain layer)."""
        self.content_template = generated_text
        self.updated_at = datetime.now(UTC)
