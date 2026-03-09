"""Campaign Service — Concrete PostgreSQL repository implementation."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from services.campaign.domain.model.campaign import Campaign
from services.campaign.domain.model.value_objects import (
    ABVariant,
    CampaignStatus,
    CampaignType,
)
from services.campaign.domain.repository import CampaignRepository
from services.campaign.infrastructure.orm_models import CampaignORM, VariantORM


class PostgresCampaignRepository(CampaignRepository):
    """Concrete repository — bridges Campaign domain model <-> ORM model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, campaign: Campaign) -> Campaign:
        existing = await self._session.get(CampaignORM, campaign.id)

        if existing:
            await self._session.execute(
                update(CampaignORM).where(CampaignORM.id == campaign.id).values(**self._to_orm_dict(campaign))
            )
        else:
            orm = CampaignORM(**self._to_orm_dict(campaign), id=campaign.id)
            self._session.add(orm)

        # Sync variants: delete existing and re-insert
        await self._session.execute(delete(VariantORM).where(VariantORM.campaign_id == campaign.id))
        for variant in campaign.variants:
            v_orm = VariantORM(
                id=variant.variant_id,
                campaign_id=campaign.id,
                content=variant.content,
                weight=variant.weight,
                impressions=variant.impressions,
                clicks=variant.clicks,
                conversions=variant.conversions,
            )
            self._session.add(v_orm)

        await self._session.flush()
        return campaign

    async def find_by_id(self, campaign_id: uuid.UUID) -> Campaign | None:
        result = await self._session.get(CampaignORM, campaign_id)
        if not result:
            return None
        variants = await self._load_variants(campaign_id)
        return self._to_domain(result, variants)

    async def find_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: str | None = None,
        campaign_type: str | None = None,
    ) -> list[Campaign]:
        stmt = select(CampaignORM)
        if status:
            stmt = stmt.where(CampaignORM.status == status)
        if campaign_type:
            stmt = stmt.where(CampaignORM.campaign_type == campaign_type)
        stmt = stmt.offset(skip).limit(limit)
        results = await self._session.scalars(stmt)
        campaigns: list[Campaign] = []
        for r in results.all():
            variants = await self._load_variants(r.id)
            campaigns.append(self._to_domain(r, variants))
        return campaigns

    async def delete(self, campaign_id: uuid.UUID) -> bool:
        result = await self._session.get(CampaignORM, campaign_id)
        if not result:
            return False
        await self._session.execute(delete(VariantORM).where(VariantORM.campaign_id == campaign_id))
        await self._session.delete(result)
        return True

    # ── Private helpers ────────────────────────────────────────

    async def _load_variants(self, campaign_id: uuid.UUID) -> list[VariantORM]:
        stmt = select(VariantORM).where(VariantORM.campaign_id == campaign_id)
        results = await self._session.scalars(stmt)
        return list(results.all())

    def _to_orm_dict(self, campaign: Campaign) -> dict[str, Any]:
        return {
            "name": campaign.name,
            "campaign_type": campaign.campaign_type.value,
            "target_segment": campaign.target_segment,
            "status": campaign.status.value,
            "content_template": campaign.content_template,
            "updated_at": campaign.updated_at,
        }

    def _to_domain(self, orm: CampaignORM, variant_orms: list[VariantORM]) -> Campaign:
        variants = [
            ABVariant(
                variant_id=v.id,
                content=v.content,
                weight=v.weight,
                impressions=v.impressions,
                clicks=v.clicks,
                conversions=v.conversions,
            )
            for v in variant_orms
        ]

        return Campaign(
            id=orm.id,
            name=orm.name,
            campaign_type=CampaignType(orm.campaign_type),
            target_segment=orm.target_segment,
            status=CampaignStatus(orm.status),
            content_template=orm.content_template or "",
            variants=variants,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
