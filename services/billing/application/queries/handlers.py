"""Billing Service — Query Handlers (CQRS read side)."""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.billing.infrastructure.orm_models import DisputeORM, InvoiceORM


@dataclass
class InvoiceDTO:
    """Data Transfer Object — read-optimized invoice view."""

    id: str
    customer_id: str
    period: str
    amount: str
    currency: str
    status: str
    dispute_status: str | None = None
    line_items: list[dict[str, str]] | None = None


@dataclass
class DisputeDTO:
    """Data Transfer Object — read-optimized dispute view."""

    id: str
    invoice_id: str
    customer_id: str
    reason: str
    status: str
    resolution: str | None = None
    refund_amount: str | None = None


class BillingQueryHandlers:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_invoice(self, invoice_id: str) -> InvoiceDTO | None:
        try:
            uid = uuid.UUID(invoice_id)
        except ValueError:
            return None
        result = await self._session.get(InvoiceORM, uid)
        if not result:
            return None
        return self._to_invoice_dto(result)

    async def list_invoices(self, customer_id: str) -> list[InvoiceDTO]:
        try:
            uid = uuid.UUID(customer_id)
        except ValueError:
            return []
        stmt = select(InvoiceORM).where(InvoiceORM.customer_id == uid)
        results = await self._session.scalars(stmt)
        return [self._to_invoice_dto(r) for r in results.all()]

    async def get_disputes(self, invoice_id: str) -> list[DisputeDTO]:
        try:
            uid = uuid.UUID(invoice_id)
        except ValueError:
            return []
        stmt = select(DisputeORM).where(DisputeORM.invoice_id == uid)
        results = await self._session.scalars(stmt)
        return [
            DisputeDTO(
                id=str(r.id),
                invoice_id=str(r.invoice_id),
                customer_id=str(r.customer_id),
                reason=r.reason,
                status=r.status,
                resolution=r.resolution,
                refund_amount=str(r.refund_amount) if r.refund_amount else None,
            )
            for r in results.all()
        ]

    def _to_invoice_dto(self, orm: InvoiceORM) -> InvoiceDTO:
        return InvoiceDTO(
            id=str(orm.id),
            customer_id=str(orm.customer_id),
            period=f"{orm.period_year}-{orm.period_month:02d}",
            amount=str(orm.amount),
            currency=orm.currency,
            status=orm.status,
            dispute_status=orm.dispute_status,
            line_items=orm.line_items,
        )
