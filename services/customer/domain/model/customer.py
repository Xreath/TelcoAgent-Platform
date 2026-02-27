"""Customer Domain — Aggregate Root."""

from datetime import datetime, timezone

from shared.models.base import AggregateRoot
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
        self.updated_at = datetime.now(timezone.utc)

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
        self.updated_at = datetime.now(timezone.utc)
