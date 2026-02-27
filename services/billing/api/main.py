"""Billing Service — FastAPI application entry point."""

from contextlib import asynccontextmanager
from decimal import Decimal

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from services.billing.domain.model.invoice import Invoice
from services.billing.domain.model.value_objects import BillingPeriod, Currency, InvoiceStatus, Money
from services.billing.infrastructure.orm_models import DisputeORM, InvoiceORM
from shared.utils.database import Base, engine, get_db_session


@asynccontextmanager
async def lifespan(app: FastAPI):
    from services.billing.infrastructure.orm_models import DisputeORM, InvoiceORM  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Billing Service",
    description="TelcoAgent Platform — Billing Bounded Context",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

router_prefix = "/v1/billing"


# ── Request schemas ────────────────────────────────────────

class CreateInvoiceRequest(BaseModel):
    customer_id: str
    period_year: int
    period_month: int
    amount: float
    currency: str = "TRY"
    line_items: list[dict] = []


class OpenDisputeRequest(BaseModel):
    reason: str


class ResolveDisputeRequest(BaseModel):
    resolution: str
    refund_amount: float | None = None


# ── Endpoints ──────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "billing-service"}


@app.post(f"{router_prefix}/invoices", status_code=status.HTTP_201_CREATED)
async def create_invoice(
    body: CreateInvoiceRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Create invoice for a customer billing period."""
    import uuid
    invoice = Invoice.create(
        customer_id=body.customer_id,
        period=BillingPeriod(year=body.period_year, month=body.period_month),
        amount=Money(amount=Decimal(str(body.amount)), currency=Currency(body.currency)),
        line_items=body.line_items,
    )

    orm = InvoiceORM(
        id=invoice.id,
        customer_id=uuid.UUID(body.customer_id),
        period_year=body.period_year,
        period_month=body.period_month,
        amount=invoice.amount.amount,
        currency=invoice.amount.currency.value,
        status=invoice.status.value,
        line_items=body.line_items,
    )
    session.add(orm)

    return {"id": str(invoice.id), "status": invoice.status.value, "amount": str(invoice.amount)}


@app.get(f"{router_prefix}/invoices")
async def list_invoices(
    customer_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[dict]:
    """List invoices for a customer — CQRS read model."""
    import uuid
    stmt = select(InvoiceORM).where(InvoiceORM.customer_id == uuid.UUID(customer_id))
    results = await session.scalars(stmt)
    return [
        {
            "id": str(r.id),
            "customer_id": str(r.customer_id),
            "period": f"{r.period_year}-{r.period_month:02d}",
            "amount": str(r.amount),
            "currency": r.currency,
            "status": r.status,
        }
        for r in results.all()
    ]


@app.post(f"{router_prefix}/invoices/{{invoice_id}}/dispute", status_code=status.HTTP_201_CREATED)
async def open_dispute(
    invoice_id: str,
    body: OpenDisputeRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Open a billing dispute — triggers BillingAnalystAgent."""
    import uuid
    orm = await session.get(InvoiceORM, uuid.UUID(invoice_id))
    if not orm:
        raise HTTPException(status_code=404, detail="Invoice not found")

    dispute = DisputeORM(
        invoice_id=uuid.UUID(invoice_id),
        customer_id=orm.customer_id,
        reason=body.reason,
        status="open",
    )
    session.add(dispute)
    orm.status = InvoiceStatus.DISPUTED.value

    return {"id": str(dispute.id), "status": "open", "invoice_id": invoice_id}
