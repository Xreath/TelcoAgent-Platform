"""Campaign Domain — MCP Server.

Exposes campaign management and generation tools via Model Context Protocol.
CampaignAgent connects to this server for dynamic tool discovery.

Run standalone:
    python -m infrastructure.mcp.campaign_mcp_server
"""

from __future__ import annotations

import json
import random
import uuid
from datetime import UTC, datetime
from typing import Annotated

import httpx
from fastmcp import FastMCP

from shared.config.settings import get_settings

mcp = FastMCP(
    "Campaign Domain MCP Server",
    instructions="Provides campaign management, segmentation, and A/B testing tools for AI agents",
)

settings = get_settings()
CAMPAIGN_SERVICE_URL = settings.campaign_service_url
CUSTOMER_SERVICE_URL = settings.customer_service_url


# ── Tools ─────────────────────────────────────────────────────


@mcp.tool()
async def get_customer_segment(
    customer_id: Annotated[str, "UUID of the customer"],
) -> str:
    """Fetch customer segment and profile data for campaign targeting.

    Returns segment (gold/silver/bronze/new/platinum), subscription plan, CLV score.
    Use this to determine which campaigns are appropriate for a customer.
    """
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


@mcp.tool()
async def generate_campaign_text(
    campaign_type: Annotated[str, "Type: sms | email | push | in_app"],
    target_segment: Annotated[str, "Target segment: gold | silver | bronze | new | platinum"],
    product: Annotated[str, "Product or offer to promote"],
    tone: Annotated[str, "Tone: formal | friendly | urgent | exclusive"] = "friendly",
    language: Annotated[str, "Language: tr | en"] = "tr",
) -> str:
    """Generate campaign text using LLM for a specific segment and channel.

    Returns generated text variants for A/B testing.
    In production, this calls the LLM; here it returns template-based mock content.
    """
    templates = {
        "sms": {
            "formal": (
                f"Sayın Müşterimiz, {product} kampanyamızdan yararlanmak için son gün yaklaşıyor."
                " Detaylar için 2880'i arayın."
            ),
            "friendly": f"Merhaba! 🎉 {product} fırsatı seni bekliyor! Hemen başvur, kaçırma! Detay: 2880",
            "urgent": f"⏰ SON 24 SAAT! {product} kampanyası bitiyor. Hemen SMS ile EVET yaz!",
            "exclusive": f"💎 VIP müşterimize özel: {product}. Sadece {target_segment} segment için. Detay: 2880",
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
            "formal": f"{product} kampanyası başladı. Detaylar için uygulamayı açın.",
            "friendly": f"🎁 {product} fırsatı! Hemen bak 👀",
            "urgent": f"⏰ {product} — Son saatler!",
            "exclusive": f"💎 Sadece sana özel: {product}",
        },
    }

    channel_templates = templates.get(campaign_type, templates["sms"])
    main_text = channel_templates.get(tone, channel_templates["friendly"])

    variants = [
        {"variant_id": "A", "content": main_text, "weight": 0.5},
        {"variant_id": "B", "content": main_text.replace("!", ".").replace("🎉", "📢"), "weight": 0.5},
    ]

    return json.dumps(
        {
            "campaign_type": campaign_type,
            "target_segment": target_segment,
            "product": product,
            "tone": tone,
            "language": language,
            "variants": variants,
            "generated_at": datetime.now(UTC).isoformat(),
            "_mock": True,
        },
        indent=2,
        ensure_ascii=False,
    )


@mcp.tool()
async def log_ab_variant(
    campaign_id: Annotated[str, "UUID of the campaign"],
    variant_id: Annotated[str, "Variant identifier (A, B, C, ...)"],
    event_type: Annotated[str, "Event: impression | click | conversion"],
    customer_id: Annotated[str | None, "UUID of the customer (optional)"] = None,
) -> str:
    """Log an A/B test event for a campaign variant.

    Tracks impressions, clicks, and conversions for each variant.
    Use this to measure campaign performance and determine winning variants.
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


@mcp.tool()
async def list_campaigns(
    status: Annotated[str | None, "Filter: draft | active | paused | completed. None for all."] = None,
    target_segment: Annotated[str | None, "Filter by target segment. None for all."] = None,
) -> str:
    """List campaigns with optional filters.

    Returns JSON array of campaigns with their status and performance metrics.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            params = {}
            if status:
                params["status"] = status
            if target_segment:
                params["target_segment"] = target_segment
            resp = await client.get(f"{CAMPAIGN_SERVICE_URL}/campaigns", params=params)
            resp.raise_for_status()
            return json.dumps(resp.json(), indent=2, ensure_ascii=False)
        except (httpx.HTTPStatusError, httpx.ConnectError):
            campaigns = [
                {
                    "id": str(uuid.uuid4()),
                    "name": f"Kampanya {i}",
                    "campaign_type": random.choice(["sms", "email", "push"]),
                    "target_segment": target_segment or random.choice(["gold", "silver"]),
                    "status": status or random.choice(["active", "draft"]),
                    "impressions": random.randint(1000, 50000),
                    "clicks": random.randint(100, 5000),
                    "conversions": random.randint(10, 500),
                    "_mock": True,
                }
                for i in range(1, 4)
            ]
            return json.dumps(campaigns, indent=2, ensure_ascii=False)


@mcp.tool()
async def get_variant_performance(
    campaign_id: Annotated[str, "UUID of the campaign"],
) -> str:
    """Get A/B variant performance metrics for a campaign.

    Returns per-variant metrics: impressions, clicks, conversions, CTR, conversion rate.
    Use this to determine which variant is winning.
    """
    variants = []
    for vid in ["A", "B"]:
        impressions = random.randint(5000, 20000)
        clicks = random.randint(int(impressions * 0.02), int(impressions * 0.15))
        conversions = random.randint(int(clicks * 0.05), int(clicks * 0.3))
        variants.append(
            {
                "variant_id": vid,
                "impressions": impressions,
                "clicks": clicks,
                "conversions": conversions,
                "ctr_pct": round(clicks / impressions * 100, 2),
                "conversion_rate_pct": round(conversions / clicks * 100, 2) if clicks > 0 else 0,
            }
        )

    winner = max(variants, key=lambda v: v["conversion_rate_pct"])
    return json.dumps(
        {
            "campaign_id": campaign_id,
            "variants": variants,
            "recommended_winner": winner["variant_id"],
            "confidence_pct": round(random.uniform(85, 99), 1),
            "_mock": True,
        },
        indent=2,
        ensure_ascii=False,
    )


# ── Resources ─────────────────────────────────────────────────


@mcp.resource("campaign://types")
def get_campaign_types() -> str:
    """Available campaign types and their channels."""
    return json.dumps(
        {
            "sms": "Kısa mesaj kampanyası — 160 karakter limit",
            "email": "E-posta kampanyası — HTML destekli, zengin içerik",
            "push": "Push bildirim — Mobil uygulama üzerinden",
            "in_app": "Uygulama içi banner veya popup",
        },
        indent=2,
        ensure_ascii=False,
    )


@mcp.resource("campaign://segments")
def get_target_segments() -> str:
    """Target segments for campaign targeting."""
    return json.dumps(
        {
            "new": "Yeni müşteriler — hoş geldin kampanyaları",
            "bronze": "Düşük CLV — upsell fırsatları",
            "silver": "Orta CLV — sadakat kampanyaları",
            "gold": "Yüksek CLV — VIP teklifler",
            "platinum": "En yüksek CLV — özel ayrıcalıklar",
            "churn_risk": "Churn riski olan müşteriler — retention kampanyaları",
        },
        indent=2,
        ensure_ascii=False,
    )


# ── Entry point ───────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
