"""Tests for Invoice Aggregate Root — CQRS write side domain logic."""

from decimal import Decimal

import pytest

from services.billing.domain.model.events import (
    BillingAnomalyFound,
    DisputeOpened,
    DisputeResolved,
    InvoiceCreated,
    InvoicePaid,
)
from services.billing.domain.model.invoice import Invoice
from services.billing.domain.model.value_objects import (
    BillingPeriod,
    Currency,
    DisputeStatus,
    InvoiceStatus,
    Money,
)


@pytest.fixture
def issued_invoice() -> Invoice:
    """create() ile oluşturulmuş, ISSUED statüsünde bir fatura."""
    return Invoice.create(
        customer_id="cust-001",
        period=BillingPeriod(year=2026, month=2),
        amount=Money(amount=Decimal("189.90"), currency=Currency.TRY),
        line_items=[{"desc": "Postpaid plan", "amount": "189.90"}],
    )


# ── Invoice.create() ─────────────────────────────────────────


class TestInvoiceCreate:
    def test_create_sets_status_issued(self, issued_invoice: Invoice):
        assert issued_invoice.status == InvoiceStatus.ISSUED

    def test_create_sets_customer_id(self, issued_invoice: Invoice):
        assert issued_invoice.customer_id == "cust-001"

    def test_create_raises_event(self, issued_invoice: Invoice):
        events = issued_invoice.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], InvoiceCreated)
        assert events[0].customer_id == "cust-001"
        assert events[0].amount == "189.90"
        assert events[0].currency == "TRY"
        assert events[0].period_label == "2026-02"

    def test_create_stores_line_items(self, issued_invoice: Invoice):
        assert len(issued_invoice.line_items) == 1
        assert issued_invoice.line_items[0]["desc"] == "Postpaid plan"


# ── mark_paid() ──────────────────────────────────────────────


class TestInvoiceMarkPaid:
    def test_mark_paid_updates_status(self, issued_invoice: Invoice):
        issued_invoice.collect_events()
        issued_invoice.mark_paid()
        assert issued_invoice.status == InvoiceStatus.PAID
        assert issued_invoice.paid_at is not None

    def test_mark_paid_raises_event(self, issued_invoice: Invoice):
        issued_invoice.collect_events()
        issued_invoice.mark_paid()
        events = issued_invoice.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], InvoicePaid)
        assert events[0].customer_id == "cust-001"

    def test_mark_paid_on_draft_raises_error(self):
        """DRAFT statüsündeki fatura ödenemez."""
        invoice = Invoice(
            customer_id="cust-002",
            period=BillingPeriod(year=2026, month=1),
            amount=Money(amount=Decimal("100")),
            status=InvoiceStatus.DRAFT,
        )
        with pytest.raises(ValueError, match="Cannot pay invoice"):
            invoice.mark_paid()

    def test_mark_paid_on_disputed_raises_error(self):
        """DISPUTED statüsündeki fatura ödenemez."""
        invoice = Invoice(
            customer_id="cust-002",
            period=BillingPeriod(year=2026, month=1),
            amount=Money(amount=Decimal("100")),
            status=InvoiceStatus.DISPUTED,
        )
        with pytest.raises(ValueError, match="Cannot pay invoice"):
            invoice.mark_paid()


# ── open_dispute() ───────────────────────────────────────────


class TestInvoiceOpenDispute:
    def test_open_dispute_updates_status(self, issued_invoice: Invoice):
        issued_invoice.collect_events()
        issued_invoice.open_dispute(reason="Hatalı tutar")
        assert issued_invoice.dispute_status == DisputeStatus.OPEN
        assert issued_invoice.status == InvoiceStatus.DISPUTED

    def test_open_dispute_raises_event(self, issued_invoice: Invoice):
        issued_invoice.collect_events()
        issued_invoice.open_dispute(reason="Hatalı tutar")
        events = issued_invoice.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], DisputeOpened)
        assert events[0].reason == "Hatalı tutar"

    def test_open_dispute_when_already_open_raises(self, issued_invoice: Invoice):
        """Zaten açık dispute varsa tekrar açılamaz."""
        issued_invoice.open_dispute(reason="İlk")
        with pytest.raises(ValueError, match="already open"):
            issued_invoice.open_dispute(reason="İkinci")


# ── resolve_dispute() ────────────────────────────────────────


class TestInvoiceResolveDispute:
    def test_resolve_dispute_updates_status(self, issued_invoice: Invoice):
        issued_invoice.open_dispute(reason="Test")
        issued_invoice.collect_events()
        issued_invoice.resolve_dispute(resolution="İade yapıldı")
        assert issued_invoice.dispute_status == DisputeStatus.RESOLVED

    def test_resolve_dispute_raises_event(self, issued_invoice: Invoice):
        issued_invoice.open_dispute(reason="Test")
        issued_invoice.collect_events()
        issued_invoice.resolve_dispute(resolution="İade yapıldı")
        events = issued_invoice.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], DisputeResolved)
        assert events[0].resolution == "İade yapıldı"

    def test_resolve_with_refund(self, issued_invoice: Invoice):
        issued_invoice.open_dispute(reason="Test")
        issued_invoice.collect_events()
        refund = Money(amount=Decimal("50.00"))
        issued_invoice.resolve_dispute(resolution="Kısmi iade", refund_amount=refund)
        events = issued_invoice.collect_events()
        assert events[0].refund_amount == "50.00"

    def test_resolve_without_open_dispute_raises(self, issued_invoice: Invoice):
        """Açık dispute yokken resolve etmeye çalışmak hata vermeli."""
        with pytest.raises(ValueError, match="No open dispute"):
            issued_invoice.resolve_dispute(resolution="Test")


# ── flag_anomaly() ───────────────────────────────────────────


class TestInvoiceFlagAnomaly:
    def test_flag_anomaly_raises_event(self, issued_invoice: Invoice):
        issued_invoice.collect_events()
        expected = Money(amount=Decimal("120.00"))
        issued_invoice.flag_anomaly(
            anomaly_type="overcharge",
            expected_amount=expected,
            description="Test anomaly",
        )
        events = issued_invoice.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], BillingAnomalyFound)
        assert events[0].anomaly_type == "overcharge"
        assert events[0].expected_amount == "120.00"
        assert events[0].actual_amount == "189.90"
