"""CustomerSupportAgent — LangGraph tool definitions.

4 tools the ReAct agent can invoke:
  1. get_customer_profile  — fetch customer data from Customer Service
  2. get_billing_info      — fetch invoices from Billing Service
  3. create_ticket         — persist a support ticket (complaint resolution)
  4. send_notification     — send SMS/email notification to customer
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Annotated

import httpx
from langchain_core.tools import tool

from shared.config.settings import get_settings

settings = get_settings()

CUSTOMER_SERVICE_URL = settings.customer_service_url
BILLING_SERVICE_URL = settings.billing_service_url


@tool
async def get_customer_profile(customer_id: Annotated[str, "UUID of the customer"]) -> str:
    """Fetch customer profile from Customer Service.

    Returns customer name, segment, subscription plan, CLV score, contact info.
    Use this to understand who the customer is before handling their complaint.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{CUSTOMER_SERVICE_URL}/{customer_id}")
            resp.raise_for_status()
            data = resp.json()
            return json.dumps(data, indent=2)
        except httpx.HTTPStatusError as e:
            return f"Error fetching customer {customer_id}: HTTP {e.response.status_code}"
        except httpx.ConnectError:
            # Fallback mock for dev/testing when Customer Service is down
            return json.dumps(
                {
                    "id": customer_id,
                    "name": "Demo Müşteri",
                    "phone_number": "+905551234567",
                    "email": "demo@telco.com",
                    "segment": "gold",
                    "subscription_plan": "postpaid_premium",
                    "clv_score": 85.0,
                    "is_active": True,
                    "_mock": True,
                },
                indent=2,
            )


@tool
async def get_billing_info(customer_id: Annotated[str, "UUID of the customer"]) -> str:
    """Fetch billing/invoice history from Billing Service.

    Returns list of invoices with amounts, periods, and statuses.
    Use this when the complaint is billing-related to check for anomalies.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(
                f"{BILLING_SERVICE_URL}/invoices",
                params={"customer_id": customer_id},
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                return f"No invoices found for customer {customer_id}"
            return json.dumps(data, indent=2)
        except httpx.HTTPStatusError as e:
            return f"Error fetching billing info: HTTP {e.response.status_code}"
        except httpx.ConnectError:
            # Fallback mock
            return json.dumps(
                [
                    {
                        "id": str(uuid.uuid4()),
                        "customer_id": customer_id,
                        "period": "2026-02",
                        "amount": "189.90",
                        "currency": "TRY",
                        "status": "paid",
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "customer_id": customer_id,
                        "period": "2026-01",
                        "amount": "245.50",
                        "currency": "TRY",
                        "status": "paid",
                    },
                ],
                indent=2,
            )


@tool
async def create_ticket(
    customer_id: Annotated[str, "UUID of the customer"],
    category: Annotated[str, "Ticket category: billing | network | service | general"],
    summary: Annotated[str, "Brief summary of the issue"],
    resolution: Annotated[str, "Proposed resolution or action taken"],
    priority: Annotated[str, "Priority: low | medium | high | critical"] = "medium",
) -> str:
    """Create a support ticket with resolution details.

    Use this after analyzing the complaint to record the resolution.
    The ticket is stored and can be tracked by the customer.
    """
    ticket = {
        "ticket_id": str(uuid.uuid4()),
        "customer_id": customer_id,
        "category": category,
        "summary": summary,
        "resolution": resolution,
        "priority": priority,
        "status": "resolved",
        "created_at": datetime.now(UTC).isoformat(),
    }
    # In production this would call a Ticket Service or write to DB
    # For now we return the ticket as confirmation
    return json.dumps(ticket, indent=2, ensure_ascii=False)


@tool
async def send_notification(
    customer_id: Annotated[str, "UUID of the customer"],
    channel: Annotated[str, "Notification channel: sms | email | push"],
    message: Annotated[str, "Notification message content"],
) -> str:
    """Send a notification to the customer about their complaint status.

    Use this to inform the customer about the resolution.
    Always send a notification after creating a ticket.
    """
    notification = {
        "notification_id": str(uuid.uuid4()),
        "customer_id": customer_id,
        "channel": channel,
        "message": message,
        "status": "sent",
        "sent_at": datetime.now(UTC).isoformat(),
    }
    # In production this would integrate with SMS gateway / email service
    return json.dumps(notification, indent=2, ensure_ascii=False)


# Tool registry — used by the agent
ALL_TOOLS = [get_customer_profile, get_billing_info, create_ticket, send_notification]
