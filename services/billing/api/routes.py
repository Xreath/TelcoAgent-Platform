"""Billing Service — FastAPI REST endpoints (v1)."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from services.billing.application.commands.handlers import (
    BillingCommandHandlers,
    CreateInvoiceCommand,
    MarkInvoicePaidCommand,
    OpenDisputeCommand,
    ResolveDisputeCommand,
)
from services.billing.application.queries.handlers import (
    BillingQueryHandlers,
    InvoiceDTO,
)
from shared.utils.database import get_db_session

router = APIRouter(prefix="/v1/billing", tags=["billing"])


# ── Request schemas ────────────────────────────────────────


class CreateInvoiceRequest(BaseModel):
    customer_id: str
    period_year: int
    period_month: int = Field(ge=1, le=12)
    amount: float = Field(gt=0)
    currency: str = "TRY"
    line_items: list[dict[str, str]] = []


class OpenDisputeRequest(BaseModel):
    reason: str


class ResolveDisputeRequest(BaseModel):
    resolution: str
    refund_amount: float | None = None


# ── Endpoints ──────────────────────────────────────────────


@router.post("/invoices", status_code=status.HTTP_201_CREATED)
async def create_invoice(
    body: CreateInvoiceRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Create invoice for a customer billing period."""
    handlers = BillingCommandHandlers(session)
    invoice = await handlers.handle_create_invoice(
        CreateInvoiceCommand(
            customer_id=body.customer_id,
            period_year=body.period_year,
            period_month=body.period_month,
            amount=body.amount,
            currency=body.currency,
            line_items=body.line_items,
        )
    )
    return {"id": str(invoice.id), "status": invoice.status.value, "amount": str(invoice.amount)}


@router.get("/invoices")
async def list_invoices(
    customer_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[InvoiceDTO]:
    """List invoices for a customer — CQRS read model."""
    handlers = BillingQueryHandlers(session)
    return await handlers.list_invoices(customer_id)


@router.get("/invoices/{invoice_id}")
async def get_invoice(
    invoice_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> InvoiceDTO:
    """Get a single invoice by ID."""
    handlers = BillingQueryHandlers(session)
    result = await handlers.get_invoice(str(invoice_id))
    if not result:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return result


@router.post("/invoices/{invoice_id}/pay")
async def mark_paid(
    invoice_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Mark an invoice as paid."""
    handlers = BillingCommandHandlers(session)
    try:
        await handlers.handle_mark_paid(MarkInvoicePaidCommand(invoice_id=str(invoice_id)))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "paid", "invoice_id": str(invoice_id)}


@router.post("/invoices/{invoice_id}/dispute", status_code=status.HTTP_201_CREATED)
async def open_dispute(
    invoice_id: UUID,
    body: OpenDisputeRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Open a billing dispute — triggers BillingAnalystAgent."""
    handlers = BillingCommandHandlers(session)
    try:
        await handlers.handle_open_dispute(OpenDisputeCommand(invoice_id=str(invoice_id), reason=body.reason))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "dispute opened", "invoice_id": str(invoice_id)}


@router.post("/invoices/{invoice_id}/resolve-dispute")
async def resolve_dispute(
    invoice_id: UUID,
    body: ResolveDisputeRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Resolve an open billing dispute."""
    handlers = BillingCommandHandlers(session)
    try:
        await handlers.handle_resolve_dispute(
            ResolveDisputeCommand(
                invoice_id=str(invoice_id),
                resolution=body.resolution,
                refund_amount=body.refund_amount,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "dispute resolved", "invoice_id": str(invoice_id)}
