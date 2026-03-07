"""Customer Service — Query Handlers (CQRS read side)."""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.customer.infrastructure.orm_models import ComplaintORM, CustomerORM


@dataclass
class CustomerDTO:
    """Data Transfer Object — read-optimized customer view."""

    id: str
    name: str
    phone_number: str
    email: str | None
    segment: str
    subscription_plan: str
    clv_score: float
    is_active: bool
    address: dict[str, str] | None = None


@dataclass
class ComplaintDTO:
    id: str
    customer_id: str
    complaint_type: str
    description: str
    priority: str
    status: str


class CustomerQueryHandlers:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_customer(self, customer_id: str) -> CustomerDTO | None:
        try:
            uid = uuid.UUID(customer_id)
        except ValueError:
            return None
        result = await self._session.get(CustomerORM, uid)
        if not result:
            return None
        return self._to_dto(result)

    async def list_customers(self, skip: int = 0, limit: int = 50) -> list[CustomerDTO]:
        stmt = select(CustomerORM).where(CustomerORM.is_active == True).offset(skip).limit(limit)  # noqa: E712
        results = await self._session.scalars(stmt)
        return [self._to_dto(r) for r in results.all()]

    async def get_complaints(self, customer_id: str) -> list[ComplaintDTO]:
        try:
            uid = uuid.UUID(customer_id)
        except ValueError:
            return []
        stmt = select(ComplaintORM).where(ComplaintORM.customer_id == uid).order_by(ComplaintORM.created_at.desc())
        results = await self._session.scalars(stmt)
        return [
            ComplaintDTO(
                id=str(r.id),
                customer_id=str(r.customer_id),
                complaint_type=r.complaint_type,
                description=r.description,
                priority=r.priority,
                status=r.status,
            )
            for r in results.all()
        ]

    async def get_by_segment(self, segment: str) -> list[CustomerDTO]:
        stmt = select(CustomerORM).where(
            CustomerORM.segment == segment,
            CustomerORM.is_active == True,  # noqa: E712
        )
        results = await self._session.scalars(stmt)
        return [self._to_dto(r) for r in results.all()]

    def _to_dto(self, orm: CustomerORM) -> CustomerDTO:
        return CustomerDTO(
            id=str(orm.id),
            name=orm.name,
            phone_number=orm.phone_number,
            email=orm.email,
            segment=orm.segment,
            subscription_plan=orm.subscription_plan,
            clv_score=orm.clv_score,
            is_active=orm.is_active,
            address=orm.address,
        )
