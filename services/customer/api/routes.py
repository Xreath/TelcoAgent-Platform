"""Customer Service — FastAPI REST endpoints (v1)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from services.customer.application.commands.handlers import (
    ChangeSegmentCommand,
    CustomerCommandHandlers,
    FileComplaintCommand,
    RegisterCustomerCommand,
)
from services.customer.application.queries.handlers import CustomerDTO, CustomerQueryHandlers
from shared.utils.database import get_db_session

router = APIRouter(prefix="/v1/customers", tags=["customers"])

# ── Request / Response schemas ─────────────────────────────

class RegisterCustomerRequest(BaseModel):
    name: str
    phone_number: str
    email: str | None = None
    subscription_plan: str = "prepaid_basic"


class FileComplaintRequest(BaseModel):
    complaint_type: str  # billing | network | service | general
    description: str
    priority: str = "medium"  # low | medium | high | critical


class ChangeSegmentRequest(BaseModel):
    new_segment: str
    reason: str


# ── Endpoints ──────────────────────────────────────────────

@router.post("/", status_code=status.HTTP_201_CREATED)
async def register_customer(
    body: RegisterCustomerRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CustomerDTO:
    """Register a new telecom customer."""
    handlers = CustomerCommandHandlers(session)
    customer = await handlers.handle_register(
        RegisterCustomerCommand(
            name=body.name,
            phone_number=body.phone_number,
            email=body.email,
            subscription_plan=body.subscription_plan,
        )
    )
    return CustomerDTO(
        id=str(customer.id),
        name=customer.name,
        phone_number=customer.phone_number.full_number,
        email=customer.email,
        segment=customer.segment.value,
        subscription_plan=customer.subscription_plan.value,
        clv_score=customer.clv_score,
        is_active=customer.is_active,
    )


@router.get("/")
async def list_customers(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    skip: int = 0,
    limit: int = 50,
) -> list[CustomerDTO]:
    """List all active customers."""
    handlers = CustomerQueryHandlers(session)
    return await handlers.list_customers(skip=skip, limit=limit)


@router.get("/{customer_id}")
async def get_customer(
    customer_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CustomerDTO:
    """Get a single customer by ID."""
    handlers = CustomerQueryHandlers(session)
    customer = await handlers.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.post("/{customer_id}/complaints", status_code=status.HTTP_201_CREATED)
async def file_complaint(
    customer_id: str,
    body: FileComplaintRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """File a complaint — triggers CustomerSupportAgent via Kafka."""
    handlers = CustomerCommandHandlers(session)
    try:
        await handlers.handle_file_complaint(
            FileComplaintCommand(
                customer_id=customer_id,
                complaint_type=body.complaint_type,
                description=body.description,
                priority=body.priority,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "complaint filed", "customer_id": customer_id}


@router.get("/{customer_id}/complaints")
async def get_complaints(
    customer_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """List all complaints for a customer."""
    handlers = CustomerQueryHandlers(session)
    return await handlers.get_complaints(customer_id)


@router.patch("/{customer_id}/segment")
async def change_segment(
    customer_id: str,
    body: ChangeSegmentRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Change customer segment (gold, silver, etc.)."""
    handlers = CustomerCommandHandlers(session)
    try:
        await handlers.handle_change_segment(
            ChangeSegmentCommand(
                customer_id=customer_id,
                new_segment=body.new_segment,
                reason=body.reason,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "segment updated", "customer_id": customer_id}
