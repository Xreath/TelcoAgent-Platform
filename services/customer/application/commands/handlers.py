"""Customer Service — Command Handlers (CQRS write side)."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from services.customer.domain.model.customer import Customer
from services.customer.domain.model.value_objects import CustomerSegment, PhoneNumber, SubscriptionPlan
from services.customer.infrastructure.kafka_publisher import OutboxRepository
from services.customer.infrastructure.postgres_repository import PostgresCustomerRepository


@dataclass
class RegisterCustomerCommand:
    name: str
    phone_number: str
    email: str | None = None
    subscription_plan: str = "prepaid_basic"


@dataclass
class FileComplaintCommand:
    customer_id: str
    complaint_type: str
    description: str
    priority: str = "medium"


@dataclass
class ChangeSegmentCommand:
    customer_id: str
    new_segment: str
    reason: str


class CustomerCommandHandlers:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PostgresCustomerRepository(session)
        self._outbox = OutboxRepository(session)

    async def handle_register(self, cmd: RegisterCustomerCommand) -> Customer:
        """Register a new customer — saves to DB + writes events to outbox."""
        phone = PhoneNumber(number=cmd.phone_number.replace("+90", ""))
        plan = SubscriptionPlan(cmd.subscription_plan)

        customer = Customer.create(
            name=cmd.name,
            phone_number=phone,
            email=cmd.email,
            subscription_plan=plan,
        )

        await self._repo.save(customer)

        # Publish all collected domain events to outbox
        for event in customer.collect_events():
            await self._outbox.save(event)

        return customer

    async def handle_file_complaint(self, cmd: FileComplaintCommand) -> None:
        """File a complaint — triggers ComplaintFiled domain event."""
        import uuid

        customer = await self._repo.find_by_id(uuid.UUID(cmd.customer_id))
        if not customer:
            raise ValueError(f"Customer {cmd.customer_id} not found")

        customer.file_complaint(
            complaint_type=cmd.complaint_type,
            description=cmd.description,
            priority=cmd.priority,
        )

        await self._repo.save(customer)

        for event in customer.collect_events():
            await self._outbox.save(event)

    async def handle_change_segment(self, cmd: ChangeSegmentCommand) -> None:
        """Change customer segment — triggers SegmentChanged domain event."""
        import uuid

        customer = await self._repo.find_by_id(uuid.UUID(cmd.customer_id))
        if not customer:
            raise ValueError(f"Customer {cmd.customer_id} not found")

        customer.change_segment(
            new_segment=CustomerSegment(cmd.new_segment),
            reason=cmd.reason,
        )

        await self._repo.save(customer)

        for event in customer.collect_events():
            await self._outbox.save(event)
