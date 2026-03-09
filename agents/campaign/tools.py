"""CampaignAgent — Tool definitions.

3 tools for campaign management:
  1. get_customer_segment   — fetch customer segment for targeting
  2. generate_campaign_text — generate campaign content with A/B variants
  3. log_ab_variant         — log A/B test events (impression, click, conversion)
"""

from __future__ import annotations

import json
import random
import uuid
from datetime import UTC, datetime
from typing import Annotated

from langchain_core.tools import tool

from shared.config.settings import get_settings

settings = get_settings()
CUSTOMER_SERVICE_URL = settings.customer_service_url


@tool
async def get_customer_segment(
    customer_id: Annotated[str, "UUID of the customer"],
) -> str:
    """Fetch customer segment and profile data for campaign targeting.

    Returns segment (gold/silver/bronze/new/platinum), subscription plan, CLV score.
    Use this to determine which campaigns are appropriate for a customer.
    """
    import httpx

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{CUSTOMER_SERVICE_URL}/{customer_id}")
            resp.raise_for_status()
            data = resp.json()
            return json.dumps(
                {
                    "customer_id": data.get("id", customer_id),
                    "segment": data.get("segment", "silver"),
                    "subscription_plan": data.get("subscription_plan", "postpaid"),
                    "clv_score": data.get("clv_score", 50.0),
                    "is_active": data.get("is_active", True),
                },
                indent=2,
            )
        except (httpx.HTTPStatusError, httpx.ConnectError):
            return json.dumps(
                {
                    "customer_id": customer_id,
                    "segment": random.choice(["gold", "silver", "bronze"]),
                    "subscription_plan": "postpaid_premium",
                    "clv_score": round(random.uniform(30, 95), 1),
                    "is_active": True,
                    "_mock": True,
                },
                indent=2,
            )


@tool
async def generate_campaign_text(
    campaign_type: Annotated[str, "Channel: sms | email | push | in_app"],
    target_segment: Annotated[str, "Target: gold | silver | bronze | new | platinum | churn_risk"],
    product: Annotated[str, "Product or offer to promote"],
    tone: Annotated[str, "Tone: formal | friendly | urgent | exclusive"] = "friendly",
) -> str:
    """Generate campaign text with A/B variants for the specified channel and segment.

    Returns two variants (A and B) with 50/50 traffic split.
    In production this would call the LLM; here it uses templates.
    Use this after determining the target segment via get_customer_segment.
    """
    templates = {
        "sms": {
            "formal": f"Sayın Müşterimiz, {product} kampanyamızdan yararlanmak için son gün yaklaşıyor. Detaylar: 2880",
            "friendly": f"Merhaba! {product} fırsatı seni bekliyor! Hemen başvur, kaçırma! Detay: 2880",
            "urgent": f"SON 24 SAAT! {product} kampanyası bitiyor. Hemen SMS ile EVET yaz!",
            "exclusive": f"VIP müşterimize özel: {product}. Sadece {target_segment} segment için. Detay: 2880",
        },
        "email": {
            "formal": (
                f"Değerli Müşterimiz,\n\n{product} kampanyamızı bilgilerinize sunarız."
                "\n\nSaygılarımızla,\nTelcoAgent"
            ),
            "friendly": f"Merhaba!\n\nSana özel {product} fırsatını kaçırma!\n\nSevgilerle,\nTelcoAgent Ekibi",
            "urgent": f"Son Şans!\n\n{product} kampanyası bitmek üzere. Hemen başvur!\n\nTelcoAgent",
            "exclusive": (
                f"Özel Davet\n\n{target_segment} müşterimiz olarak {product} ayrıcalığına sahipsiniz."
                "\n\nTelcoAgent VIP"
            ),
        },
        "push": {
            "formal": f"{product} kampanyası başladı.",
            "friendly": f"{product} fırsatı! Hemen bak",
            "urgent": f"{product} — Son saatler!",
            "exclusive": f"Sadece sana özel: {product}",
        },
    }

    channel_templates = templates.get(campaign_type, templates["sms"])
    main_text = channel_templates.get(tone, channel_templates["friendly"])

    variants = [
        {"variant_id": "A", "content": main_text, "weight": 0.5},
        {"variant_id": "B", "content": main_text.replace("!", ".").replace("Hemen", "Şimdi"), "weight": 0.5},
    ]

    return json.dumps(
        {
            "campaign_type": campaign_type,
            "target_segment": target_segment,
            "product": product,
            "tone": tone,
            "variants": variants,
            "generated_at": datetime.now(UTC).isoformat(),
        },
        indent=2,
        ensure_ascii=False,
    )


@tool
async def log_ab_variant(
    campaign_id: Annotated[str, "UUID of the campaign"],
    variant_id: Annotated[str, "Variant identifier (A or B)"],
    event_type: Annotated[str, "Event: impression | click | conversion"],
    customer_id: Annotated[str | None, "UUID of the customer (optional)"] = None,
) -> str:
    """Log an A/B test event for tracking campaign performance.

    Events: impression (seen), click (engaged), conversion (completed action).
    Use this to track which variant performs better.
    """
    event = {
        "event_id": str(uuid.uuid4()),
        "campaign_id": campaign_id,
        "variant_id": variant_id,
        "event_type": event_type,
        "customer_id": customer_id,
        "logged_at": datetime.now(UTC).isoformat(),
    }
    return json.dumps(event, indent=2, ensure_ascii=False)


ALL_TOOLS = [get_customer_segment, generate_campaign_text, log_ab_variant]
