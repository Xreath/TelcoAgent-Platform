"""Customer Domain — Value Objects."""

from enum import StrEnum

from shared.models.base import ValueObject


class CustomerSegment(StrEnum):
    """Customer segmentation based on CLV and behavior."""

    PLATINUM = "platinum"
    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"
    NEW = "new"
    CHURNING = "churning"


class PhoneNumber(ValueObject):
    """Turkish phone number value object."""

    country_code: str = "+90"
    number: str  # e.g. "5551234567"

    @property
    def full_number(self) -> str:
        return f"{self.country_code}{self.number}"

    def __str__(self) -> str:
        return self.full_number


class Address(ValueObject):
    """Customer address."""

    city: str
    district: str
    postal_code: str
    full_address: str


class SubscriptionPlan(StrEnum):
    """Telecom subscription plans."""

    PREPAID_BASIC = "prepaid_basic"
    PREPAID_PREMIUM = "prepaid_premium"
    POSTPAID_STARTER = "postpaid_starter"
    POSTPAID_BUSINESS = "postpaid_business"
    POSTPAID_ENTERPRISE = "postpaid_enterprise"
    FIBER_HOME = "fiber_home"
    FIBER_BUSINESS = "fiber_business"
