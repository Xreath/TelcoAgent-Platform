"""Billing Domain — Value Objects."""

from decimal import Decimal
from enum import Enum

from shared.models.base import ValueObject


class Currency(str, Enum):
    TRY = "TRY"
    USD = "USD"
    EUR = "EUR"


class Money(ValueObject):
    """Monetary amount with currency — immutable."""
    amount: Decimal
    currency: Currency = Currency.TRY

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def __str__(self) -> str:
        return f"{self.amount:.2f} {self.currency.value}"


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    OVERDUE = "overdue"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"


class DisputeStatus(str, Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class BillingPeriod(ValueObject):
    """Billing period — month/year combination."""
    year: int
    month: int  # 1-12

    @property
    def label(self) -> str:
        return f"{self.year}-{self.month:02d}"
