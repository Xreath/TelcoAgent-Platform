"""Campaign Service — Query Handlers (CQRS read side)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.campaign.infrastructure.orm_models import CampaignORM, VariantORM


@dataclass
class VariantDTO:
    """Data Transfer Object — read-optimized variant view."""

    variant_id: str
    content: str
    weight: float
    impressions: int
    clicks: int
    conversions: int
    click_rate: float = 0.0
    conversion_rate: float = 0.0


@dataclass
class CampaignDTO:
    """Data Transfer Object — read-optimized campaign view."""

    id: str
    name: str
    campaign_type: str
    target_segment: str
    status: str
    content_template: str
    created_at: str
    updated_at: str
    variants: list[VariantDTO] = field(default_factory=list)


class CampaignQueryHandlers:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_campaign(self, campaign_id: str) -> CampaignDTO | None:
        try:
            uid = uuid.UUID(campaign_id)
        except ValueError:
            return None
        result = await self._session.get(CampaignORM, uid)
        if not result:
            return None
        variants = await self._get_variants(uid)
        return self._to_dto(result, variants)

    async def list_campaigns(
        self,
        skip: int = 0,
        limit: int = 50,
        status: str | None = None,
        campaign_type: str | None = None,
    ) -> list[CampaignDTO]:
        stmt = select(CampaignORM)
        if status:
            stmt = stmt.where(CampaignORM.status == status)
        if campaign_type:
            stmt = stmt.where(CampaignORM.campaign_type == campaign_type)
        stmt = stmt.order_by(CampaignORM.created_at.desc()).offset(skip).limit(limit)
        results = await self._session.scalars(stmt)
        dtos: list[CampaignDTO] = []
        for r in results.all():
            variants = await self._get_variants(r.id)
            dtos.append(self._to_dto(r, variants))
        return dtos

    async def get_variants(self, campaign_id: str) -> list[VariantDTO]:
        try:
            uid = uuid.UUID(campaign_id)
        except ValueError:
            return []
        return await self._get_variants(uid)

    async def _get_variants(self, campaign_id: uuid.UUID) -> list[VariantDTO]:
        stmt = select(VariantORM).where(VariantORM.campaign_id == campaign_id)
        results = await self._session.scalars(stmt)
        return [self._to_variant_dto(r) for r in results.all()]

    def _to_dto(self, orm: CampaignORM, variants: list[VariantDTO]) -> CampaignDTO:
        return CampaignDTO(
            id=str(orm.id),
            name=orm.name,
            campaign_type=orm.campaign_type,
            target_segment=orm.target_segment,
            status=orm.status,
            content_template=orm.content_template or "",
            created_at=orm.created_at.isoformat(),
            updated_at=orm.updated_at.isoformat(),
            variants=variants,
        )

    def _to_variant_dto(self, orm: VariantORM) -> VariantDTO:
        impressions = orm.impressions or 0
        clicks = orm.clicks or 0
        conversions = orm.conversions or 0
        return VariantDTO(
            variant_id=str(orm.id),
            content=orm.content,
            weight=orm.weight,
            impressions=impressions,
            clicks=clicks,
            conversions=conversions,
            click_rate=clicks / impressions if impressions > 0 else 0.0,
            conversion_rate=conversions / impressions if impressions > 0 else 0.0,
        )
