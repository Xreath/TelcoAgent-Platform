"""Network Service — Concrete PostgreSQL repository implementation."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from services.network.domain.model.network_node import NetworkNode
from services.network.domain.model.value_objects import Location, NodeStatus, NodeType
from services.network.domain.repository import NetworkNodeRepository
from services.network.infrastructure.orm_models import NetworkNodeORM


class PostgresNetworkNodeRepository(NetworkNodeRepository):
    """Concrete repository — bridges domain model <-> ORM model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, node: NetworkNode) -> NetworkNode:
        existing = await self._session.get(NetworkNodeORM, node.id)

        if existing:
            # Update existing record
            await self._session.execute(
                update(NetworkNodeORM).where(NetworkNodeORM.id == node.id).values(**self._to_orm_dict(node))
            )
        else:
            # Insert new record
            orm = NetworkNodeORM(**self._to_orm_dict(node), id=node.id)
            self._session.add(orm)

        await self._session.flush()
        return node

    async def find_by_id(self, node_id: uuid.UUID) -> NetworkNode | None:
        result = await self._session.get(NetworkNodeORM, node_id)
        return self._to_domain(result) if result else None

    async def find_by_hostname(self, hostname: str) -> NetworkNode | None:
        stmt = select(NetworkNodeORM).where(NetworkNodeORM.hostname == hostname)
        result = await self._session.scalar(stmt)
        return self._to_domain(result) if result else None

    async def find_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: str | None = None,
        node_type: str | None = None,
        region: str | None = None,
    ) -> list[NetworkNode]:
        stmt = select(NetworkNodeORM)

        if status:
            stmt = stmt.where(NetworkNodeORM.status == status)
        if node_type:
            stmt = stmt.where(NetworkNodeORM.node_type == node_type)
        if region:
            stmt = stmt.where(NetworkNodeORM.region == region)

        stmt = stmt.offset(skip).limit(limit)
        results = await self._session.scalars(stmt)
        return [self._to_domain(r) for r in results.all()]

    async def delete(self, node_id: uuid.UUID) -> bool:
        result = await self._session.get(NetworkNodeORM, node_id)
        if not result:
            return False
        await self._session.delete(result)
        return True

    # -- Mapping helpers -------------------------------------------

    def _to_orm_dict(self, node: NetworkNode) -> dict[str, Any]:
        return {
            "hostname": node.hostname,
            "node_type": node.node_type.value,
            "status": node.status.value,
            "lat": node.location.lat,
            "lng": node.location.lng,
            "region": node.location.region,
            "ip_address": node.ip_address,
            "firmware_version": node.firmware_version,
            "updated_at": node.updated_at,
        }

    def _to_domain(self, orm: NetworkNodeORM) -> NetworkNode:
        location = Location(lat=orm.lat, lng=orm.lng, region=orm.region)

        return NetworkNode(
            id=orm.id,
            hostname=orm.hostname,
            node_type=NodeType(orm.node_type),
            status=NodeStatus(orm.status),
            location=location,
            ip_address=orm.ip_address,
            firmware_version=orm.firmware_version,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
