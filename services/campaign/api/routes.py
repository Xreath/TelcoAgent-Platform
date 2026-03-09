"""Campaign Service — FastAPI REST endpoints (v1)."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from services.campaign.application.commands.handlers import (
    AddVariantCommand,
    CampaignCommandHandlers,
    CreateCampaignCommand,
    GenerateCampaignTextCommand,
    UpdateCampaignStatusCommand,
)
from services.campaign.application.queries.handlers import (
    CampaignDTO,
    CampaignQueryHandlers,
    VariantDTO,
)
from shared.utils.database import get_db_session

router = APIRouter(prefix="/v1/campaigns", tags=["campaigns"])


# ── Request schemas ────────────────────────────────────────


class CreateCampaignRequest(BaseModel):
    name: str
    campaign_type: str  # sms | email | push | in_app
    target_segment: str
    content_template: str = ""


class UpdateStatusRequest(BaseModel):
    new_status: str  # draft | active | paused | completed | archived


class AddVariantRequest(BaseModel):
    content: str
    weight: float = Field(default=0.5, ge=0.0, le=1.0)


# ── Endpoints ──────────────────────────────────────────────


@router.get("/")
async def list_campaigns(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    skip: int = 0,
    limit: int = 50,
    status_filter: str | None = None,
    type_filter: str | None = None,
) -> list[CampaignDTO]:
    """List campaigns with optional filters by status and type."""
    handlers = CampaignQueryHandlers(session)
    return await handlers.list_campaigns(
        skip=skip,
        limit=limit,
        status=status_filter,
        campaign_type=type_filter,
    )


@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CampaignDTO:
    """Get a single campaign by ID."""
    handlers = CampaignQueryHandlers(session)
    result = await handlers.get_campaign(str(campaign_id))
    if not result:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return result


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_campaign(
    body: CreateCampaignRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Create a new campaign."""
    handlers = CampaignCommandHandlers(session)
    campaign = await handlers.handle_create_campaign(
        CreateCampaignCommand(
            name=body.name,
            campaign_type=body.campaign_type,
            target_segment=body.target_segment,
            content_template=body.content_template,
        )
    )
    return {
        "id": str(campaign.id),
        "name": campaign.name,
        "status": campaign.status.value,
        "campaign_type": campaign.campaign_type.value,
        "target_segment": campaign.target_segment,
    }


@router.patch("/{campaign_id}/status")
async def update_campaign_status(
    campaign_id: UUID,
    body: UpdateStatusRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Update campaign status (with transition validation)."""
    handlers = CampaignCommandHandlers(session)
    try:
        await handlers.handle_update_status(
            UpdateCampaignStatusCommand(
                campaign_id=str(campaign_id),
                new_status=body.new_status,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "updated", "campaign_id": str(campaign_id), "new_status": body.new_status}


@router.post("/{campaign_id}/variants", status_code=status.HTTP_201_CREATED)
async def add_variant(
    campaign_id: UUID,
    body: AddVariantRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Add an A/B variant to a campaign."""
    handlers = CampaignCommandHandlers(session)
    try:
        campaign = await handlers.handle_add_variant(
            AddVariantCommand(
                campaign_id=str(campaign_id),
                content=body.content,
                weight=body.weight,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "status": "variant added",
        "campaign_id": str(campaign_id),
        "total_variants": len(campaign.variants),
    }


@router.get("/{campaign_id}/variants")
async def list_variants(
    campaign_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[VariantDTO]:
    """List A/B variants with performance metrics for a campaign."""
    handlers = CampaignQueryHandlers(session)
    return await handlers.get_variants(str(campaign_id))


@router.post("/{campaign_id}/generate")
async def generate_campaign_text(
    campaign_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Trigger LLM-based campaign text generation (mock)."""
    handlers = CampaignCommandHandlers(session)
    try:
        campaign = await handlers.handle_generate_text(
            GenerateCampaignTextCommand(campaign_id=str(campaign_id))
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "campaign_id": str(campaign_id),
        "generated_content": campaign.content_template,
    }
