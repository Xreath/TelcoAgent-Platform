"""Campaign Domain — Abstract Repository Interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from services.campaign.domain.model.campaign import Campaign


class CampaignRepository(ABC):
    """Abstract repository — infrastructure layer provides concrete implementation."""

    @abstractmethod
    async def save(self, campaign: Campaign) -> Campaign: ...

    @abstractmethod
    async def find_by_id(self, campaign_id: UUID) -> Campaign | None: ...

    @abstractmethod
    async def find_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: str | None = None,
        campaign_type: str | None = None,
    ) -> list[Campaign]: ...

    @abstractmethod
    async def delete(self, campaign_id: UUID) -> bool: ...
