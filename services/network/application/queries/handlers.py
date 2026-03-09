"""Network Service — Query Handlers (CQRS read side)."""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.network.infrastructure.orm_models import NetworkNodeORM


@dataclass
class NetworkNodeDTO:
    """Data Transfer Object — read-optimized network node view."""

    id: str
    hostname: str
    node_type: str
    status: str
    ip_address: str | None
    firmware_version: str | None
    location: dict[str, object]


@dataclass
class NodeMetricsDTO:
    """Mock metrics data transfer object."""

    node_id: str
    hostname: str
    latency_ms: float
    packet_loss_pct: float
    throughput_mbps: float
    uptime_pct: float


class NetworkQueryHandlers:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_node(self, node_id: str) -> NetworkNodeDTO | None:
        try:
            uid = uuid.UUID(node_id)
        except ValueError:
            return None
        result = await self._session.get(NetworkNodeORM, uid)
        if not result:
            return None
        return self._to_dto(result)

    async def list_nodes(
        self,
        skip: int = 0,
        limit: int = 50,
        status: str | None = None,
        node_type: str | None = None,
        region: str | None = None,
    ) -> list[NetworkNodeDTO]:
        stmt = select(NetworkNodeORM)

        if status:
            stmt = stmt.where(NetworkNodeORM.status == status)
        if node_type:
            stmt = stmt.where(NetworkNodeORM.node_type == node_type)
        if region:
            stmt = stmt.where(NetworkNodeORM.region == region)

        stmt = stmt.offset(skip).limit(limit)
        results = await self._session.scalars(stmt)
        return [self._to_dto(r) for r in results.all()]

    async def get_node_metrics(self, node_id: str) -> NodeMetricsDTO | None:
        """Return mock metrics for a node. In production these come from monitoring infra."""
        try:
            uid = uuid.UUID(node_id)
        except ValueError:
            return None
        result = await self._session.get(NetworkNodeORM, uid)
        if not result:
            return None

        return NodeMetricsDTO(
            node_id=str(result.id),
            hostname=result.hostname,
            latency_ms=round(random.uniform(5.0, 150.0), 2),
            packet_loss_pct=round(random.uniform(0.0, 3.0), 2),
            throughput_mbps=round(random.uniform(20.0, 200.0), 2),
            uptime_pct=round(random.uniform(95.0, 100.0), 2),
        )

    def _to_dto(self, orm: NetworkNodeORM) -> NetworkNodeDTO:
        return NetworkNodeDTO(
            id=str(orm.id),
            hostname=orm.hostname,
            node_type=orm.node_type,
            status=orm.status,
            ip_address=orm.ip_address,
            firmware_version=orm.firmware_version,
            location={
                "lat": orm.lat,
                "lng": orm.lng,
                "region": orm.region,
            },
        )
