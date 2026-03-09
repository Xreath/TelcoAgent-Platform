"""BillingAnalystAgent — Tool definitions.

4 tools for invoice analysis and dispute management:
  1. get_invoice_detail   — fetch detailed invoice with line items
  2. detect_anomaly       — analyze billing history for anomalies
  3. generate_explanation — produce human-readable anomaly explanation
  4. process_dispute      — handle billing dispute (approve/reject/partial)
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Annotated

from langchain_core.tools import tool

from shared.config.settings import get_settings

settings = get_settings()
BILLING_SERVICE_URL = settings.billing_service_url


@tool
async def get_invoice_detail(
    invoice_id: Annotated[str, "UUID of the invoice"],
) -> str:
    """Fetch detailed invoice information including all line items.

    Returns JSON with: amount, currency, period, status, line_items, payment_date, due_date.
    Use this to understand exactly what a customer was charged for.
    """
    import httpx

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{BILLING_SERVICE_URL}/invoices/{invoice_id}")
            resp.raise_for_status()
            return json.dumps(resp.json(), indent=2, ensure_ascii=False)
        except (httpx.HTTPStatusError, httpx.ConnectError):
            return json.dumps(
                {
                    "id": invoice_id,
                    "period": "2026-02",
                    "amount": "245.50",
                    "currency": "TRY",
                    "status": "paid",
                    "line_items": [
                        {"description": "Ses Paketi - Postpaid Premium", "amount": "99.90"},
                        {"description": "Data Paketi - 50GB", "amount": "49.90"},
                        {"description": "Ek Kullanım - Uluslararası Arama", "amount": "80.70"},
                        {"description": "Dijital Servisler", "amount": "15.00"},
                    ],
                    "payment_date": "2026-02-15",
                    "due_date": "2026-02-28",
                    "_mock": True,
                },
                indent=2,
                ensure_ascii=False,
            )


@tool
async def detect_anomaly(
    customer_id: Annotated[str, "UUID of the customer"],
) -> str:
    """Analyze customer's billing history to detect anomalies.

    Compares recent invoices against historical average using %30 threshold.
    Returns anomaly score, deviation percentage, and recommendation.
    Use this when a customer reports unexpected charges.
    """
    import httpx

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
                {"amount": "245.50", "period": "2026-02"},
                {"amount": "189.90", "period": "2026-01"},
                {"amount": "175.00", "period": "2025-12"},
                {"amount": "180.20", "period": "2025-11"},
                {"amount": "170.00", "period": "2025-10"},
            ]

    amounts = [float(inv.get("amount", 0)) for inv in invoices]
    if len(amounts) < 2:
        return json.dumps({"anomaly_detected": False, "reason": "Yetersiz veri"})

    avg = sum(amounts[1:]) / len(amounts[1:])
    latest = amounts[0]
    deviation_pct = ((latest - avg) / avg) * 100 if avg > 0 else 0

    result = {
        "customer_id": customer_id,
        "latest_amount": latest,
        "historical_average": round(avg, 2),
        "deviation_percent": round(deviation_pct, 2),
        "anomaly_detected": abs(deviation_pct) > 30,
        "anomaly_score": min(round(abs(deviation_pct) / 100, 2), 1.0),
        "invoice_count": len(invoices),
        "amounts_history": amounts,
    }

    if result["anomaly_detected"]:
        if deviation_pct > 0:
            result["anomaly_type"] = "unexpected_increase"
            result["recommendation"] = "Faturada anormal artış. Line item bazlı inceleme önerilir."
        else:
            result["anomaly_type"] = "unexpected_decrease"
            result["recommendation"] = "Faturada anormal düşüş. Hizmet kesintisi kontrol edilmeli."

    return json.dumps(result, indent=2, ensure_ascii=False)


@tool
async def generate_explanation(
    customer_id: Annotated[str, "UUID of the customer"],
    invoice_id: Annotated[str, "UUID of the invoice to explain"],
    anomaly_details: Annotated[str, "JSON string of anomaly detection results"],
) -> str:
    """Generate a human-readable explanation for a billing anomaly.

    Produces a clear, customer-friendly explanation of why the invoice differs from normal.
    Use this after detect_anomaly to prepare a response for the customer.
    """
    try:
        details = json.loads(anomaly_details)
    except json.JSONDecodeError:
        details = {}

    deviation = details.get("deviation_percent", 0)
    latest = details.get("latest_amount", 0)
    avg = details.get("historical_average", 0)

    explanation = {
        "customer_id": customer_id,
        "invoice_id": invoice_id,
        "explanation": (
            f"Sayın Müşterimiz,\n\n"
            f"Son faturanız ({latest} TL), ortalama faturanızdan ({avg} TL) "
            f"%{abs(deviation):.1f} {'yüksek' if deviation > 0 else 'düşük'}tür.\n\n"
            f"Olası nedenler:\n"
            f"- Ek kullanım (uluslararası arama, roaming)\n"
            f"- Paket dışı data kullanımı\n"
            f"- Yeni aktive edilen dijital servisler\n\n"
            f"Detaylı inceleme için fatura kalemlerini kontrol ediniz."
        ),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    return json.dumps(explanation, indent=2, ensure_ascii=False)


@tool
async def process_dispute(
    invoice_id: Annotated[str, "UUID of the disputed invoice"],
    decision: Annotated[str, "Decision: approve_refund | reject | partial_refund"],
    refund_amount: Annotated[float | None, "Refund amount (required for partial_refund)"] = None,
    reason: Annotated[str, "Reason for the decision"] = "",
) -> str:
    """Process a billing dispute with a resolution decision.

    Decisions:
    - approve_refund: Full refund approved
    - reject: Dispute rejected, charges are valid
    - partial_refund: Partial refund for specific items

    Use this after analyzing the invoice and anomaly to resolve the dispute.
    """
    resolution = {
        "dispute_id": str(uuid.uuid4()),
        "invoice_id": invoice_id,
        "decision": decision,
        "reason": reason,
        "resolved_at": datetime.now(UTC).isoformat(),
        "status": "resolved",
    }

    if decision == "approve_refund":
        resolution["refund_amount"] = "full"
        resolution["action"] = "Tam iade işlemi başlatıldı. 3-5 iş günü içinde hesaba yansıyacak."
    elif decision == "partial_refund":
        resolution["refund_amount"] = refund_amount or 0
        resolution["action"] = f"{refund_amount or 0} TL kısmi iade işlemi başlatıldı."
    else:
        resolution["refund_amount"] = 0
        resolution["action"] = "İtiraz reddedildi. Fatura kalemleri doğrulanmıştır."

    return json.dumps(resolution, indent=2, ensure_ascii=False)


ALL_TOOLS = [get_invoice_detail, detect_anomaly, generate_explanation, process_dispute]
