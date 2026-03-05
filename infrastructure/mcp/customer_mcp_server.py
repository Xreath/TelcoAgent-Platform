"""Customer Domain — MCP Server.

Exposes customer-related tools via Model Context Protocol.
Agents connect to this server to discover and use customer tools dynamically.

Run standalone:
    python -m infrastructure.mcp.customer_mcp_server

Or import and mount in a larger MCP application.
"""

from __future__ import annotations

import json
import uuid
from typing import Annotated

import httpx
from fastmcp import FastMCP

mcp = FastMCP(
    "Customer Domain MCP Server",
    description="Provides customer profile, complaint, and segment tools for AI agents",
)

CUSTOMER_SERVICE_URL = "http://localhost:8001/v1/customers"


# ── Tools ─────────────────────────────────────────────────────

@mcp.tool()
async def get_customer_profile(
    customer_id: Annotated[str, "UUID of the customer"],
) -> str:
    """Fetch full customer profile including segment, subscription plan, CLV score, and contact info.

    Use this to understand the customer before handling their request.
    Returns JSON with: id, name, phone_number, email, segment, subscription_plan, clv_score, is_active.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{CUSTOMER_SERVICE_URL}/{customer_id}")
            resp.raise_for_status()
            return json.dumps(resp.json(), indent=2, ensure_ascii=False)
        except httpx.HTTPStatusError as e:
            return json.dumps({"error": f"Customer not found: HTTP {e.response.status_code}"})
        except httpx.ConnectError:
            return json.dumps({
                "id": customer_id, "name": "Demo Müşteri", "phone_number": "+905551234567",
                "email": "demo@telco.com", "segment": "gold", "subscription_plan": "postpaid_premium",
                "clv_score": 85.0, "is_active": True, "_mock": True,
            }, indent=2)


@mcp.tool()
async def list_customers(
    segment: Annotated[str | None, "Filter by segment (gold, silver, bronze, new). None for all."] = None,
    limit: Annotated[int, "Max number of customers to return"] = 20,
) -> str:
    """List active customers, optionally filtered by segment.

    Returns JSON array of customer profiles.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            params = {"limit": limit}
            resp = await client.get(CUSTOMER_SERVICE_URL, params=params)
            resp.raise_for_status()
            customers = resp.json()
            if segment:
                customers = [c for c in customers if c.get("segment") == segment]
            return json.dumps(customers, indent=2, ensure_ascii=False)
        except httpx.ConnectError:
            return json.dumps([
                {"id": str(uuid.uuid4()), "name": "Mock Müşteri 1", "segment": segment or "gold", "_mock": True},
                {"id": str(uuid.uuid4()), "name": "Mock Müşteri 2", "segment": segment or "silver", "_mock": True},
            ], indent=2)


@mcp.tool()
async def get_customer_complaints(
    customer_id: Annotated[str, "UUID of the customer"],
) -> str:
    """Fetch all complaints for a customer, ordered by most recent first.

    Returns JSON array with: id, complaint_type, description, priority, status.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{CUSTOMER_SERVICE_URL}/{customer_id}/complaints")
            resp.raise_for_status()
            return json.dumps(resp.json(), indent=2, ensure_ascii=False)
        except httpx.HTTPStatusError as e:
            return json.dumps({"error": f"HTTP {e.response.status_code}"})
        except httpx.ConnectError:
            return json.dumps([
                {"id": str(uuid.uuid4()), "customer_id": customer_id, "complaint_type": "billing",
                 "description": "Faturada fazla ücret", "priority": "high", "status": "open", "_mock": True},
            ], indent=2)


@mcp.tool()
async def file_complaint(
    customer_id: Annotated[str, "UUID of the customer"],
    complaint_type: Annotated[str, "Type: billing | network | service | general"],
    description: Annotated[str, "Detailed description of the complaint"],
    priority: Annotated[str, "Priority: low | medium | high | critical"] = "medium",
) -> str:
    """File a new complaint for a customer. This triggers the CustomerSupportAgent via Kafka.

    Returns confirmation with complaint status.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                f"{CUSTOMER_SERVICE_URL}/{customer_id}/complaints",
                json={
                    "complaint_type": complaint_type,
                    "description": description,
                    "priority": priority,
                },
            )
            resp.raise_for_status()
            return json.dumps(resp.json(), indent=2, ensure_ascii=False)
        except httpx.HTTPStatusError as e:
            return json.dumps({"error": f"HTTP {e.response.status_code}", "detail": e.response.text})
        except httpx.ConnectError:
            return json.dumps({
                "status": "complaint filed (mock)",
                "customer_id": customer_id,
                "complaint_type": complaint_type,
                "_mock": True,
            }, indent=2)


@mcp.tool()
async def change_customer_segment(
    customer_id: Annotated[str, "UUID of the customer"],
    new_segment: Annotated[str, "New segment: new | bronze | silver | gold | platinum"],
    reason: Annotated[str, "Reason for the segment change"],
) -> str:
    """Change a customer's segment (upgrade/downgrade).

    Use when a customer qualifies for a different tier based on CLV, usage, or retention.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.patch(
                f"{CUSTOMER_SERVICE_URL}/{customer_id}/segment",
                json={"new_segment": new_segment, "reason": reason},
            )
            resp.raise_for_status()
            return json.dumps(resp.json(), indent=2, ensure_ascii=False)
        except httpx.HTTPStatusError as e:
            return json.dumps({"error": f"HTTP {e.response.status_code}"})
        except httpx.ConnectError:
            return json.dumps({"status": "segment updated (mock)", "customer_id": customer_id, "_mock": True})


# ── Resources ─────────────────────────────────────────────────

@mcp.resource("customer://segments")
def get_segments() -> str:
    """Available customer segments and their descriptions."""
    return json.dumps({
        "new": "Yeni kayıt olmuş müşteri, henüz sınıflandırılmamış",
        "bronze": "Düşük CLV, prepaid, minimal kullanım",
        "silver": "Orta CLV, aktif kullanıcı",
        "gold": "Yüksek CLV, sadık müşteri, öncelikli destek",
        "platinum": "En yüksek CLV, VIP, özel müşteri temsilcisi",
    }, indent=2, ensure_ascii=False)


@mcp.resource("customer://complaint-types")
def get_complaint_types() -> str:
    """Available complaint types and their descriptions."""
    return json.dumps({
        "billing": "Fatura, ödeme, ücretlendirme sorunları",
        "network": "Ağ bağlantısı, sinyal, hız sorunları",
        "service": "Hizmet kalitesi, müşteri hizmetleri sorunları",
        "general": "Genel şikayet ve geri bildirimler",
    }, indent=2, ensure_ascii=False)


# ── Entry point ───────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
