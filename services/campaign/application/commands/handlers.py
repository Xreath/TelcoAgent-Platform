"""Campaign Service — Command Handlers (CQRS write side)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from services.campaign.domain.model.campaign import Campaign
from services.campaign.domain.model.value_objects import CampaignStatus, CampaignType
from services.campaign.domain.services import CampaignOptimizationService
from services.campaign.infrastructure.kafka_publisher import OutboxRepository
from services.campaign.infrastructure.postgres_repository import PostgresCampaignRepository


@dataclass
class CreateCampaignCommand:
    name: str
    campaign_type: str
    target_segment: str
    content_template: str = ""


@dataclass
class UpdateCampaignStatusCommand:
    campaign_id: str
    new_status: str


@dataclass
class AddVariantCommand:
    campaign_id: str
    content: str
    weight: float = 0.5


@dataclass
class GenerateCampaignTextCommand:
    campaign_id: str


class CampaignCommandHandlers:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PostgresCampaignRepository(session)
        self._outbox = OutboxRepository(session)

    async def handle_create_campaign(self, cmd: CreateCampaignCommand) -> Campaign:
        """Create a new campaign — saves to DB + writes events to outbox."""
        campaign = Campaign.create(
            name=cmd.name,
            campaign_type=CampaignType(cmd.campaign_type),
            target_segment=cmd.target_segment,
            content_template=cmd.content_template,
        )

        await self._repo.save(campaign)

        for event in campaign.collect_events():
            await self._outbox.save(event)

        return campaign

    async def handle_update_status(self, cmd: UpdateCampaignStatusCommand) -> None:
        """Update campaign status with transition validation."""
        campaign = await self._repo.find_by_id(uuid.UUID(cmd.campaign_id))
        if not campaign:
            raise ValueError(f"Campaign {cmd.campaign_id} not found")

        campaign.update_status(CampaignStatus(cmd.new_status))
        await self._repo.save(campaign)

        for event in campaign.collect_events():
            await self._outbox.save(event)

    async def handle_add_variant(self, cmd: AddVariantCommand) -> Campaign:
        """Add an A/B variant to a campaign."""
        campaign = await self._repo.find_by_id(uuid.UUID(cmd.campaign_id))
        if not campaign:
            raise ValueError(f"Campaign {cmd.campaign_id} not found")

        campaign.add_variant(content=cmd.content, weight=cmd.weight)
        await self._repo.save(campaign)

        for event in campaign.collect_events():
            await self._outbox.save(event)

        return campaign

    async def handle_generate_text(self, cmd: GenerateCampaignTextCommand) -> Campaign:
        """Trigger LLM-based campaign text generation (mock)."""
        campaign = await self._repo.find_by_id(uuid.UUID(cmd.campaign_id))
        if not campaign:
            raise ValueError(f"Campaign {cmd.campaign_id} not found")

        generated = CampaignOptimizationService.generate_campaign_text_mock(
            campaign_name=campaign.name,
            campaign_type=campaign.campaign_type.value,
            target_segment=campaign.target_segment,
            template=campaign.content_template,
        )
        campaign.generate_content(generated)
        await self._repo.save(campaign)

        return campaign
