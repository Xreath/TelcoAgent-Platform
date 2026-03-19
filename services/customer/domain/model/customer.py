"""Customer Domain — Aggregate Root."""

from datetime import UTC, datetime

from services.customer.domain.model.events import (
    ComplaintFiled,
    CustomerCreated,
    CustomerSegmentChanged,
)
from services.customer.domain.model.value_objects import (
    Address,
    CustomerSegment,
    PhoneNumber,
    SubscriptionPlan,
)
from pydantic import PrivateAttr

from shared.models.base import AggregateRoot


class PendingComplaint:
    """Transient complaint data held by the aggregate until persisted."""

    __slots__ = ("complaint_type", "description", "priority")

    def __init__(self, complaint_type: str, description: str, priority: str) -> None:
        self.complaint_type = complaint_type
        self.description = description
        self.priority = priority


class Customer(AggregateRoot):
    """Customer Aggregate Root — the consistency boundary for customer data."""

    name: str
    phone_number: PhoneNumber
    email: str | None = None
    address: Address | None = None
    segment: CustomerSegment = CustomerSegment.NEW
    subscription_plan: SubscriptionPlan = SubscriptionPlan.PREPAID_BASIC
    clv_score: float = 0.0  # Customer Lifetime Value
    is_active: bool = True

    _pending_complaints: list[PendingComplaint] = PrivateAttr(default_factory=list)

    def collect_complaints(self) -> list[PendingComplaint]:
        """Return and clear pending complaints — same pattern as collect_events()."""
        complaints = self._pending_complaints.copy()
        self._pending_complaints.clear()
        return complaints

    @classmethod
    def create(
        cls,
        name: str,
        phone_number: PhoneNumber,
        email: str | None = None,
        subscription_plan: SubscriptionPlan = SubscriptionPlan.PREPAID_BASIC,
    ) -> "Customer":
        """Factory method — creates customer and raises CustomerCreated event."""
        customer = cls(
            name=name,
            phone_number=phone_number,
            email=email,
            subscription_plan=subscription_plan,
        )
        customer.add_event(
            CustomerCreated(
                aggregate_id=str(customer.id),
                name=name,
                phone_number=str(phone_number),
                segment=customer.segment.value,
            )
        )
        return customer

    def change_segment(self, new_segment: CustomerSegment, reason: str) -> None:
        """Change customer segment and raise domain event."""
        if new_segment == self.segment:
            return

        old_segment = self.segment
        self.segment = new_segment
        self.updated_at = datetime.now(UTC)

        self.add_event(
            CustomerSegmentChanged(
                aggregate_id=str(self.id),
                old_segment=old_segment.value,
                new_segment=new_segment.value,
                reason=reason,
            )
        )

    def file_complaint(
        self,
        complaint_type: str,
        description: str,
        priority: str = "medium",
    ) -> None:
        """File a complaint and raise domain event."""
        self._pending_complaints.append(
            PendingComplaint(complaint_type=complaint_type, description=description, priority=priority)
        )
        self.add_event(
            ComplaintFiled(
                aggregate_id=str(self.id),
                complaint_type=complaint_type,
                description=description,
                priority=priority,
            )
        )

    def deactivate(self) -> None:
        """Deactivate customer account."""
        self.is_active = False
        self.updated_at = datetime.now(UTC)
