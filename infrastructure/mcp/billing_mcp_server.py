"""Billing Domain — MCP Server.

Exposes billing-related tools via Model Context Protocol.
Agents connect to this server to discover and use billing tools dynamically.

Run standalone:
    python -m infrastructure.mcp.billing_mcp_server
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Annotated

import httpx
from fastmcp import FastMCP

mcp = FastMCP(
    "Billing Domain MCP Server",
    description="Provides invoice, payment, and dispute tools for AI agents",
)

BILLING_SERVICE_URL = "http://localhost:8002/v1/billing"


# ── Tools ─────────────────────────────────────────────────────

@mcp.tool()
async def get_invoices(
    customer_id: Annotated[str, "UUID of the customer"],
) -> str:
    """Fetch all invoices for a customer.

    Returns JSON array with: id, period, amount, currency, status.
    Use this to check billing history, detect anomalies, or verify disputed amounts.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(
                f"{BILLING_SERVICE_URL}/invoices",
                params={"customer_id": customer_id},
            )
            resp.raise_for_status()
            return json.dumps(resp.json(), indent=2, ensure_ascii=False)
        except httpx.HTTPStatusError as e:
            return json.dumps({"error": f"HTTP {e.response.status_code}"})
        except httpx.ConnectError:
            return json.dumps([
                {"id": str(uuid.uuid4()), "customer_id": customer_id, "period": "2026-02",
                 "amount": "189.90", "currency": "TRY", "status": "paid", "_mock": True},
                {"id": str(uuid.uuid4()), "customer_id": customer_id, "period": "2026-01",
                 "amount": "245.50", "currency": "TRY", "status": "paid", "_mock": True},
            ], indent=2)


@mcp.tool()
async def get_invoice_detail(
    invoice_id: Annotated[str, "UUID of the invoice"],
) -> str:
    """Fetch detailed information for a specific invoice including line items.

    Returns JSON with full invoice details: amount, line items, status, disputes.
    """
    # In production, this would call a specific endpoint
    # For now, return a detailed mock
    return json.dumps({
        "id": invoice_id,
        "period": "2026-02",
        "amount": "189.90",
        "currency": "TRY",
        "status": "paid",
        "line_items": [
            {"description": "Ses Paketi - Postpaid Premium", "amount": "99.90"},
            {"description": "Data Paketi - 50GB", "amount": "49.90"},
            {"description": "Ek Kullanım - Uluslararası Arama", "amount": "25.10"},
            {"description": "Dijital Servisler", "amount": "15.00"},
        ],
        "payment_date": "2026-02-15",
        "due_date": "2026-02-28",
        "_mock": True,
    }, indent=2, ensure_ascii=False)


@mcp.tool()
async def open_dispute(
    invoice_id: Annotated[str, "UUID of the disputed invoice"],
    reason: Annotated[str, "Detailed reason for the dispute"],
) -> str:
    """Open a billing dispute for an invoice.

    This marks the invoice as disputed and triggers the BillingAnalystAgent.
    Returns dispute confirmation with tracking ID.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                f"{BILLING_SERVICE_URL}/invoices/{invoice_id}/dispute",
                json={"reason": reason},
            )
            resp.raise_for_status()
            return json.dumps(resp.json(), indent=2, ensure_ascii=False)
        except httpx.HTTPStatusError as e:
            return json.dumps({"error": f"HTTP {e.response.status_code}", "detail": e.response.text})
        except httpx.ConnectError:
            return json.dumps({
                "id": str(uuid.uuid4()),
                "invoice_id": invoice_id,
                "reason": reason,
                "status": "open",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "_mock": True,
            }, indent=2, ensure_ascii=False)


@mcp.tool()
async def calculate_billing_anomaly(
    customer_id: Annotated[str, "UUID of the customer"],
) -> str:
    """Analyze a customer's billing history to detect anomalies.

    Compares recent invoices against historical average.
    Returns anomaly score and details if any unusual patterns are found.
    """
    # Fetch invoices first
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(
                f"{BILLING_SERVICE_URL}/invoices",
                params={"customer_id": customer_id},
            )
            resp.raise_for_status()
            invoices = resp.json()
        except (httpx.HTTPStatusError, httpx.ConnectError):
            invoices = [
                {"amount": "189.90", "period": "2026-02"},
                {"amount": "245.50", "period": "2026-01"},
                {"amount": "175.00", "period": "2025-12"},
                {"amount": "180.20", "period": "2025-11"},
            ]

    # Simple anomaly detection: flag if latest is >30% above average
    amounts = [float(inv.get("amount", 0)) for inv in invoices]
    if len(amounts) < 2:
        return json.dumps({"anomaly_detected": False, "reason": "Insufficient data"})

    avg = sum(amounts[1:]) / len(amounts[1:])
    latest = amounts[0]
    deviation_pct = ((latest - avg) / avg) * 100 if avg > 0 else 0

    result = {
        "customer_id": customer_id,
        "latest_amount": latest,
        "historical_average": round(avg, 2),
        "deviation_percent": round(deviation_pct, 2),
        "anomaly_detected": abs(deviation_pct) > 30,
        "invoice_count": len(invoices),
    }

    if result["anomaly_detected"]:
        result["recommendation"] = (
            "Faturada anormal artış tespit edildi. "
            "Müşteriye bilgi verilmesi ve detaylı inceleme önerilir."
        )

    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
async def create_invoice(
    customer_id: Annotated[str, "UUID of the customer"],
    period_year: Annotated[int, "Invoice year (e.g. 2026)"],
    period_month: Annotated[int, "Invoice month (1-12)"],
    amount: Annotated[float, "Total invoice amount"],
    currency: Annotated[str, "Currency code"] = "TRY",
) -> str:
    """Create a new invoice for a customer.

    Used primarily by billing batch jobs or manual adjustments.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                f"{BILLING_SERVICE_URL}/invoices",
                json={
                    "customer_id": customer_id,
                    "period_year": period_year,
                    "period_month": period_month,
                    "amount": amount,
                    "currency": currency,
                },
            )
            resp.raise_for_status()
            return json.dumps(resp.json(), indent=2, ensure_ascii=False)
        except httpx.HTTPStatusError as e:
            return json.dumps({"error": f"HTTP {e.response.status_code}", "detail": e.response.text})
        except httpx.ConnectError:
            return json.dumps({
                "id": str(uuid.uuid4()), "customer_id": customer_id,
                "status": "pending", "amount": str(amount), "_mock": True,
            }, indent=2)


# ── Resources ─────────────────────────────────────────────────

@mcp.resource("billing://invoice-statuses")
def get_invoice_statuses() -> str:
    """Available invoice statuses and their meanings."""
    return json.dumps({
        "pending": "Fatura oluşturuldu, ödeme bekleniyor",
        "paid": "Ödeme alındı",
        "overdue": "Ödeme süresi geçti",
        "disputed": "İtiraz açıldı, incelemede",
        "cancelled": "Fatura iptal edildi",
        "refunded": "İade yapıldı",
    }, indent=2, ensure_ascii=False)


@mcp.resource("billing://currencies")
def get_currencies() -> str:
    """Supported currencies."""
    return json.dumps({"TRY": "Türk Lirası", "USD": "ABD Doları", "EUR": "Euro"}, ensure_ascii=False)


# ── Entry point ───────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
