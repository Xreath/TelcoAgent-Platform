"""Tests for Billing Value Objects — Money, BillingPeriod, enums."""

from decimal import Decimal

import pytest

from services.billing.domain.model.value_objects import (
    BillingPeriod,
    Currency,
    DisputeStatus,
    InvoiceStatus,
    Money,
)

# ── Money ────────────────────────────────────────────────────


class TestMoney:
    def test_add_same_currency(self):
        a = Money(amount=Decimal("100.50"), currency=Currency.TRY)
        b = Money(amount=Decimal("49.50"), currency=Currency.TRY)
        result = a + b
        assert result.amount == Decimal("150.00")
        assert result.currency == Currency.TRY

    def test_add_different_currency_raises(self):
        a = Money(amount=Decimal("100"), currency=Currency.TRY)
        b = Money(amount=Decimal("50"), currency=Currency.USD)
        with pytest.raises(ValueError, match="Cannot add different currencies"):
            _ = a + b

    def test_str_format(self):
        m = Money(amount=Decimal("189.90"), currency=Currency.TRY)
        assert str(m) == "189.90 TRY"

    def test_str_format_usd(self):
        m = Money(amount=Decimal("99.99"), currency=Currency.USD)
        assert str(m) == "99.99 USD"

    def test_frozen(self):
        m = Money(amount=Decimal("100"), currency=Currency.TRY)
        try:
            m.amount = Decimal("200")
            assert False, "Should be frozen"
        except Exception:
            pass

    def test_default_currency_try(self):
        m = Money(amount=Decimal("50"))
        assert m.currency == Currency.TRY


# ── BillingPeriod ────────────────────────────────────────────


class TestBillingPeriod:
    def test_label_format(self):
        bp = BillingPeriod(year=2026, month=2)
        assert bp.label == "2026-02"

    def test_label_single_digit_month(self):
        bp = BillingPeriod(year=2026, month=1)
        assert bp.label == "2026-01"

    def test_label_december(self):
        bp = BillingPeriod(year=2025, month=12)
        assert bp.label == "2025-12"

    def test_frozen(self):
        bp = BillingPeriod(year=2026, month=3)
        try:
            bp.year = 2025
            assert False, "Should be frozen"
        except Exception:
            pass


# ── Enums ────────────────────────────────────────────────────


class TestInvoiceStatus:
    def test_values(self):
        assert InvoiceStatus.DRAFT == "draft"
        assert InvoiceStatus.ISSUED == "issued"
        assert InvoiceStatus.PAID == "paid"
        assert InvoiceStatus.OVERDUE == "overdue"
        assert InvoiceStatus.DISPUTED == "disputed"
        assert InvoiceStatus.CANCELLED == "cancelled"


class TestDisputeStatus:
    def test_values(self):
        assert DisputeStatus.OPEN == "open"
        assert DisputeStatus.UNDER_REVIEW == "under_review"
        assert DisputeStatus.RESOLVED == "resolved"
        assert DisputeStatus.REJECTED == "rejected"


class TestCurrency:
    def test_values(self):
        assert Currency.TRY == "TRY"
        assert Currency.USD == "USD"
        assert Currency.EUR == "EUR"
