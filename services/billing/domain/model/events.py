"""Billing Domain — Domain Events."""

from shared.events.base import DomainEvent


class InvoiceCreated(DomainEvent):
    event_type: str = "billing.invoice_created"
    aggregate_type: str = "Invoice"
    customer_id: str
    amount: str  # serialized Decimal
    currency: str
    period_label: str  # e.g. "2026-02"


class InvoicePaid(DomainEvent):
    event_type: str = "billing.invoice_paid"
    aggregate_type: str = "Invoice"
    customer_id: str
    amount: str
    paid_at: str


class BillingAnomalyFound(DomainEvent):
    event_type: str = "billing.anomaly_found"
    aggregate_type: str = "Invoice"
    customer_id: str
    anomaly_type: str  # "overcharge" | "duplicate" | "unexpected_charge"
    expected_amount: str
    actual_amount: str
    description: str


class DisputeOpened(DomainEvent):
    event_type: str = "billing.dispute_opened"
    aggregate_type: str = "Dispute"
    customer_id: str
    invoice_id: str
    reason: str


class DisputeResolved(DomainEvent):
    event_type: str = "billing.dispute_resolved"
    aggregate_type: str = "Dispute"
    customer_id: str
    invoice_id: str
    resolution: str
    refund_amount: str | None = None


class PaymentFailed(DomainEvent):
    event_type: str = "billing.payment_failed"
    aggregate_type: str = "Invoice"
    customer_id: str
    amount: str
    failure_reason: str
