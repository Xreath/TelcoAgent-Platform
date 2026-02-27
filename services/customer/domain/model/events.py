"""Customer Domain — Domain Events."""

from shared.events.base import DomainEvent


class CustomerCreated(DomainEvent):
    """Raised when a new customer is registered."""

    event_type: str = "customer.created"
    aggregate_type: str = "Customer"
    name: str
    phone_number: str
    segment: str


class CustomerSegmentChanged(DomainEvent):
    """Raised when customer segment changes (e.g. upgrade/downgrade)."""

    event_type: str = "customer.segment_changed"
    aggregate_type: str = "Customer"
    old_segment: str
    new_segment: str
    reason: str


class ComplaintFiled(DomainEvent):
    """Raised when a customer files a complaint."""

    event_type: str = "customer.complaint_filed"
    aggregate_type: str = "Customer"
    complaint_type: str  # "billing", "network", "service", "general"
    description: str
    priority: str  # "low", "medium", "high", "critical"


class CustomerChurnRiskDetected(DomainEvent):
    """Raised when churn prediction model flags a customer."""

    event_type: str = "customer.churn_risk_detected"
    aggregate_type: str = "Customer"
    risk_score: float  # 0.0 - 1.0
    contributing_factors: list[str]
