"""Billing Service — Concrete PostgreSQL repository implementation."""

import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from services.billing.domain.model.invoice import Invoice
from services.billing.domain.model.value_objects import (
    BillingPeriod,
    Currency,
    DisputeStatus,
    InvoiceStatus,
    Money,
)
from services.billing.domain.repository import InvoiceRepository
from services.billing.infrastructure.orm_models import InvoiceORM


class PostgresInvoiceRepository(InvoiceRepository):
    """Concrete repository — bridges Invoice domain model <-> ORM model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, invoice: Invoice) -> Invoice:
        existing = await self._session.get(InvoiceORM, invoice.id)

        if existing:
            await self._session.execute(
                update(InvoiceORM).where(InvoiceORM.id == invoice.id).values(**self._to_orm_dict(invoice))
            )
        else:
            orm = InvoiceORM(**self._to_orm_dict(invoice), id=invoice.id)
            self._session.add(orm)

        await self._session.flush()
        return invoice

    async def find_by_id(self, invoice_id: uuid.UUID) -> Invoice | None:
        result = await self._session.get(InvoiceORM, invoice_id)
        return self._to_domain(result) if result else None

    async def find_by_customer(self, customer_id: uuid.UUID) -> list[Invoice]:
        stmt = select(InvoiceORM).where(InvoiceORM.customer_id == customer_id)
        results = await self._session.scalars(stmt)
        return [self._to_domain(r) for r in results.all()]

    async def delete(self, invoice_id: uuid.UUID) -> bool:
        result = await self._session.get(InvoiceORM, invoice_id)
        if not result:
            return False
        await self._session.delete(result)
        return True

    # ── Mapping helpers ───────────────────────────────────────

    def _to_orm_dict(self, invoice: Invoice) -> dict[str, Any]:
        return {
            "customer_id": uuid.UUID(invoice.customer_id),
            "period_year": invoice.period.year,
            "period_month": invoice.period.month,
            "amount": invoice.amount.amount,
            "currency": invoice.amount.currency.value,
            "status": invoice.status.value,
            "dispute_status": invoice.dispute_status.value if invoice.dispute_status else None,
            "line_items": invoice.line_items,
            "due_date": invoice.due_date,
            "paid_at": invoice.paid_at,
            "updated_at": invoice.updated_at,
        }

    def _to_domain(self, orm: InvoiceORM) -> Invoice:
        dispute_status = DisputeStatus(orm.dispute_status) if orm.dispute_status else None

        return Invoice(
            id=orm.id,
            customer_id=str(orm.customer_id),
            period=BillingPeriod(year=orm.period_year, month=orm.period_month),
            amount=Money(amount=orm.amount, currency=Currency(orm.currency)),
            status=InvoiceStatus(orm.status),
            dispute_status=dispute_status,
            line_items=orm.line_items if orm.line_items else [],
            due_date=orm.due_date,
            paid_at=orm.paid_at,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
