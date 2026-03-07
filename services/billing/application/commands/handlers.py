"""Billing Service — Command Handlers (CQRS write side)."""

import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from services.billing.domain.model.invoice import Invoice
from services.billing.domain.model.value_objects import BillingPeriod, Currency, Money
from services.billing.infrastructure.kafka_publisher import OutboxRepository
from services.billing.infrastructure.postgres_repository import PostgresInvoiceRepository


@dataclass
class CreateInvoiceCommand:
    customer_id: str
    period_year: int
    period_month: int
    amount: float
    currency: str = "TRY"
    line_items: list[dict[str, str]] | None = None


@dataclass
class MarkInvoicePaidCommand:
    invoice_id: str


@dataclass
class OpenDisputeCommand:
    invoice_id: str
    reason: str


@dataclass
class ResolveDisputeCommand:
    invoice_id: str
    resolution: str
    refund_amount: float | None = None


class BillingCommandHandlers:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PostgresInvoiceRepository(session)
        self._outbox = OutboxRepository(session)

    async def handle_create_invoice(self, cmd: CreateInvoiceCommand) -> Invoice:
        """Create a new invoice — saves to DB + writes events to outbox."""
        invoice = Invoice.create(
            customer_id=cmd.customer_id,
            period=BillingPeriod(year=cmd.period_year, month=cmd.period_month),
            amount=Money(amount=Decimal(str(cmd.amount)), currency=Currency(cmd.currency)),
            line_items=cmd.line_items or [],
        )

        await self._repo.save(invoice)

        for event in invoice.collect_events():
            await self._outbox.save(event)

        return invoice

    async def handle_mark_paid(self, cmd: MarkInvoicePaidCommand) -> None:
        """Mark an invoice as paid."""
        invoice = await self._repo.find_by_id(uuid.UUID(cmd.invoice_id))
        if not invoice:
            raise ValueError(f"Invoice {cmd.invoice_id} not found")

        invoice.mark_paid()
        await self._repo.save(invoice)

        for event in invoice.collect_events():
            await self._outbox.save(event)

    async def handle_open_dispute(self, cmd: OpenDisputeCommand) -> None:
        """Open a dispute on an invoice."""
        invoice = await self._repo.find_by_id(uuid.UUID(cmd.invoice_id))
        if not invoice:
            raise ValueError(f"Invoice {cmd.invoice_id} not found")

        invoice.open_dispute(cmd.reason)
        await self._repo.save(invoice)

        for event in invoice.collect_events():
            await self._outbox.save(event)

    async def handle_resolve_dispute(self, cmd: ResolveDisputeCommand) -> None:
        """Resolve a dispute on an invoice."""
        invoice = await self._repo.find_by_id(uuid.UUID(cmd.invoice_id))
        if not invoice:
            raise ValueError(f"Invoice {cmd.invoice_id} not found")

        refund = None
        if cmd.refund_amount is not None:
            refund = Money(amount=Decimal(str(cmd.refund_amount)), currency=invoice.amount.currency)

        invoice.resolve_dispute(cmd.resolution, refund_amount=refund)
        await self._repo.save(invoice)

        for event in invoice.collect_events():
            await self._outbox.save(event)
