"""Network Service — FastAPI REST endpoints (v1)."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from services.network.application.commands.handlers import (
    CreateNodeCommand,
    DiagnoseNodeCommand,
    NetworkCommandHandlers,
    UpdateNodeStatusCommand,
)
from services.network.application.queries.handlers import NetworkNodeDTO, NetworkQueryHandlers, NodeMetricsDTO
from shared.utils.database import get_db_session

router = APIRouter(prefix="/v1/network", tags=["network"])

# -- Request / Response schemas ----------------------------------------


class CreateNodeRequest(BaseModel):
    hostname: str
    node_type: str  # bts | switch | router | core
    lat: float
    lng: float
    region: str
    ip_address: str | None = None
    firmware_version: str | None = None


class UpdateNodeStatusRequest(BaseModel):
    new_status: str  # active | degraded | down
    reason: str


# -- Endpoints ---------------------------------------------------------


@router.get("/nodes")
async def list_nodes(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    skip: int = 0,
    limit: int = 50,
    status_filter: str | None = None,
    node_type: str | None = None,
    region: str | None = None,
) -> list[NetworkNodeDTO]:
    """List network nodes with optional filters by status, type, and region."""
    handlers = NetworkQueryHandlers(session)
    return await handlers.list_nodes(skip=skip, limit=limit, status=status_filter, node_type=node_type, region=region)


@router.get("/nodes/{node_id}")
async def get_node(
    node_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NetworkNodeDTO:
    """Get a single network node by ID."""
    handlers = NetworkQueryHandlers(session)
    node = await handlers.get_node(str(node_id))
    if not node:
        raise HTTPException(status_code=404, detail="Network node not found")
    return node


@router.post("/nodes", status_code=status.HTTP_201_CREATED)
async def create_node(
    body: CreateNodeRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NetworkNodeDTO:
    """Create a new network node."""
    handlers = NetworkCommandHandlers(session)
    node = await handlers.handle_create_node(
        CreateNodeCommand(
            hostname=body.hostname,
            node_type=body.node_type,
            lat=body.lat,
            lng=body.lng,
            region=body.region,
            ip_address=body.ip_address,
            firmware_version=body.firmware_version,
        )
    )
    return NetworkNodeDTO(
        id=str(node.id),
        hostname=node.hostname,
        node_type=node.node_type.value,
        status=node.status.value,
        ip_address=node.ip_address,
        firmware_version=node.firmware_version,
        location={
            "lat": node.location.lat,
            "lng": node.location.lng,
            "region": node.location.region,
        },
    )


@router.patch("/nodes/{node_id}/status")
async def update_node_status(
    node_id: UUID,
    body: UpdateNodeStatusRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Update a network node's operational status."""
    handlers = NetworkCommandHandlers(session)
    try:
        await handlers.handle_update_status(
            UpdateNodeStatusCommand(
                node_id=str(node_id),
                new_status=body.new_status,
                reason=body.reason,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "node status updated", "node_id": str(node_id)}


@router.post("/nodes/{node_id}/diagnose")
async def diagnose_node(
    node_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Run diagnostic on a network node — returns metrics and anomalies."""
    handlers = NetworkCommandHandlers(session)
    try:
        result = await handlers.handle_diagnose(DiagnoseNodeCommand(node_id=str(node_id)))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@router.get("/nodes/{node_id}/metrics")
async def get_node_metrics(
    node_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NodeMetricsDTO:
    """Get current metrics for a network node (mock data)."""
    handlers = NetworkQueryHandlers(session)
    metrics = await handlers.get_node_metrics(str(node_id))
    if not metrics:
        raise HTTPException(status_code=404, detail="Network node not found")
    return metrics
