"""Customer Service — Concrete PostgreSQL repository implementation."""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from services.customer.domain.model.customer import Customer
from services.customer.domain.model.value_objects import CustomerSegment, PhoneNumber, SubscriptionPlan
from services.customer.domain.repository import CustomerRepository
from services.customer.infrastructure.orm_models import CustomerORM


class PostgresCustomerRepository(CustomerRepository):
    """Concrete repository — bridges domain model ↔ ORM model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, customer: Customer) -> Customer:
        existing = await self._session.get(CustomerORM, customer.id)

        if existing:
            # Update existing record
            await self._session.execute(
                update(CustomerORM)
                .where(CustomerORM.id == customer.id)
                .values(**self._to_orm_dict(customer))
            )
        else:
            # Insert new record
            orm = CustomerORM(**self._to_orm_dict(customer), id=customer.id)
            self._session.add(orm)

        await self._session.flush()
        return customer

    async def find_by_id(self, customer_id: uuid.UUID) -> Customer | None:
        result = await self._session.get(CustomerORM, customer_id)
        return self._to_domain(result) if result else None

    async def find_by_phone(self, phone_number: str) -> Customer | None:
        stmt = select(CustomerORM).where(CustomerORM.phone_number == phone_number)
        result = await self._session.scalar(stmt)
        return self._to_domain(result) if result else None

    async def find_all(self, skip: int = 0, limit: int = 100) -> list[Customer]:
        stmt = select(CustomerORM).offset(skip).limit(limit)
        results = await self._session.scalars(stmt)
        return [self._to_domain(r) for r in results.all()]

    async def delete(self, customer_id: uuid.UUID) -> bool:
        result = await self._session.get(CustomerORM, customer_id)
        if not result:
            return False
        await self._session.delete(result)
        return True

    # ── Mapping helpers ───────────────────────────────────────

    def _to_orm_dict(self, customer: Customer) -> dict:
        return {
            "name": customer.name,
            "phone_number": customer.phone_number.full_number,
            "email": customer.email,
            "segment": customer.segment.value,
            "subscription_plan": customer.subscription_plan.value,
            "clv_score": customer.clv_score,
            "is_active": customer.is_active,
            "address": customer.address.model_dump() if customer.address else None,
            "updated_at": customer.updated_at,
        }

    def _to_domain(self, orm: CustomerORM) -> Customer:
        # Strip country code to get just the number part
        phone_str = orm.phone_number
        if phone_str.startswith("+90"):
            number = phone_str[3:]
            phone = PhoneNumber(number=number)
        else:
            phone = PhoneNumber(country_code="", number=phone_str)

        return Customer(
            id=orm.id,
            name=orm.name,
            phone_number=phone,
            email=orm.email,
            segment=CustomerSegment(orm.segment),
            subscription_plan=SubscriptionPlan(orm.subscription_plan),
            clv_score=orm.clv_score,
            is_active=orm.is_active,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
