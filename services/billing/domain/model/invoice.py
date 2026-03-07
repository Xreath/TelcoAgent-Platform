"""Billing Domain — Invoice Aggregate Root."""

from datetime import UTC, datetime

from pydantic import Field

from services.billing.domain.model.events import (
    BillingAnomalyFound,
    DisputeOpened,
    DisputeResolved,
    InvoiceCreated,
    InvoicePaid,
)
from services.billing.domain.model.value_objects import (
    BillingPeriod,
    DisputeStatus,
    InvoiceStatus,
    Money,
)
from shared.models.base import AggregateRoot


class Invoice(AggregateRoot):
    """Invoice Aggregate Root — billing consistency boundary."""

    customer_id: str
    period: BillingPeriod
    amount: Money
    status: InvoiceStatus = InvoiceStatus.DRAFT
    due_date: datetime | None = None
    paid_at: datetime | None = None
    dispute_status: DisputeStatus | None = None
    line_items: list[dict[str, str]] = Field(default_factory=list)

    @classmethod
    def create(
        cls,
        customer_id: str,
        period: BillingPeriod,
        amount: Money,
        line_items: list[dict[str, str]] | None = None,
    ) -> "Invoice":
        invoice = cls(
            customer_id=customer_id,
            period=period,
            amount=amount,
            status=InvoiceStatus.ISSUED,
            line_items=line_items or [],
        )
        invoice.add_event(
            InvoiceCreated(
                aggregate_id=str(invoice.id),
                customer_id=customer_id,
                amount=str(amount.amount),
                currency=amount.currency.value,
                period_label=period.label,
            )
        )
        return invoice

    def mark_paid(self) -> None:
        if self.status not in (InvoiceStatus.ISSUED, InvoiceStatus.OVERDUE):
            raise ValueError(f"Cannot pay invoice in status: {self.status}")
        self.status = InvoiceStatus.PAID
        self.paid_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)
        self.add_event(
            InvoicePaid(
                aggregate_id=str(self.id),
                customer_id=self.customer_id,
                amount=str(self.amount.amount),
                paid_at=self.paid_at.isoformat(),
            )
        )

    def flag_anomaly(self, anomaly_type: str, expected_amount: Money, description: str) -> None:
        self.add_event(
            BillingAnomalyFound(
                aggregate_id=str(self.id),
                customer_id=self.customer_id,
                anomaly_type=anomaly_type,
                expected_amount=str(expected_amount.amount),
                actual_amount=str(self.amount.amount),
                description=description,
            )
        )

    def open_dispute(self, reason: str) -> None:
        if self.dispute_status == DisputeStatus.OPEN:
            raise ValueError("Dispute already open")
        self.dispute_status = DisputeStatus.OPEN
        self.status = InvoiceStatus.DISPUTED
        self.updated_at = datetime.now(UTC)
        self.add_event(
            DisputeOpened(
                aggregate_id=str(self.id),
                customer_id=self.customer_id,
                invoice_id=str(self.id),
                reason=reason,
            )
        )

    def resolve_dispute(self, resolution: str, refund_amount: Money | None = None) -> None:
        if self.dispute_status != DisputeStatus.OPEN:
            raise ValueError("No open dispute to resolve")
        self.dispute_status = DisputeStatus.RESOLVED
        self.status = InvoiceStatus.PAID if refund_amount else InvoiceStatus.ISSUED
        self.updated_at = datetime.now(UTC)
        self.add_event(
            DisputeResolved(
                aggregate_id=str(self.id),
                customer_id=self.customer_id,
                invoice_id=str(self.id),
                resolution=resolution,
                refund_amount=str(refund_amount.amount) if refund_amount else None,
            )
        )
