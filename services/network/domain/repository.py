"""Network Domain — Abstract Repository Interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from services.network.domain.model.network_node import NetworkNode


class NetworkNodeRepository(ABC):
    """Abstract repository — infrastructure layer provides concrete implementation."""

    @abstractmethod
    async def save(self, node: NetworkNode) -> NetworkNode: ...

    @abstractmethod
    async def find_by_id(self, node_id: UUID) -> NetworkNode | None: ...

    @abstractmethod
    async def find_by_hostname(self, hostname: str) -> NetworkNode | None: ...

    @abstractmethod
    async def find_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: str | None = None,
        node_type: str | None = None,
        region: str | None = None,
    ) -> list[NetworkNode]: ...

    @abstractmethod
    async def delete(self, node_id: UUID) -> bool: ...
