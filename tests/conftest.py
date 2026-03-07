"""Shared test fixtures for TelcoAgent Platform tests."""

from decimal import Decimal

import pytest

from services.billing.domain.model.value_objects import BillingPeriod, Currency, Money
from services.customer.domain.model.customer import Customer
from services.customer.domain.model.value_objects import (
    Address,
    PhoneNumber,
    SubscriptionPlan,
)


@pytest.fixture
def sample_phone_number() -> PhoneNumber:
    return PhoneNumber(country_code="+90", number="5551234567")


@pytest.fixture
def sample_address() -> Address:
    return Address(
        city="Istanbul",
        district="Kadikoy",
        postal_code="34710",
        full_address="Moda Caddesi No:1, Kadikoy, Istanbul",
    )


@pytest.fixture
def sample_customer(sample_phone_number: PhoneNumber) -> Customer:
    """Pre-built customer with factory method — includes CustomerCreated event."""
    return Customer.create(
        name="Ahmet Yilmaz",
        phone_number=sample_phone_number,
        email="ahmet@example.com",
        subscription_plan=SubscriptionPlan.POSTPAID_BUSINESS,
    )


@pytest.fixture
def sample_money() -> Money:
    return Money(amount=Decimal("189.90"), currency=Currency.TRY)


@pytest.fixture
def sample_billing_period() -> BillingPeriod:
    return BillingPeriod(year=2026, month=2)
