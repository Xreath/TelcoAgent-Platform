"""CampaignAgent — LangGraph agent for campaign generation and A/B testing.

Architecture:
  - LangGraph ReAct agent with campaign-specific tools
  - Generates personalized campaign content based on customer segments
  - Manages A/B testing variants and tracks performance
  - DeepSeek API (OpenAI-compatible) as LLM backend

Flow:
  1. Campaign request arrives (new segment event, churn risk, manual trigger)
  2. Agent fetches customer segment data
  3. Agent generates campaign text with A/B variants
  4. Agent logs variant events for performance tracking
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from agents.campaign.tools import ALL_TOOLS
from shared.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """Sen TelcoAgent platformunun Kampanya Uzmanısın (CampaignAgent).

Görevin:
1. Müşteri segmentine uygun kampanya oluşturmak
2. A/B test varyantları üretmek
3. Kampanya performansını takip etmek

Çalışma Süreci:
1. Müşteri segmentini kontrol et (get_customer_segment)
2. Segmente ve kanala uygun kampanya metni üret (generate_campaign_text)
3. A/B varyant eventlerini logla (log_ab_variant)

Segment-Kanal Stratejisi:
- platinum/gold → exclusive tone, email + sms
- silver → friendly tone, sms + push
- bronze/new → urgent tone, push + in_app
- churn_risk → exclusive tone, sms + email (retention odaklı)

Kampanya Türleri:
- Upsell: Daha yüksek paket önerisi
- Cross-sell: Ek hizmet önerisi (dijital servisler, sigorta)
- Retention: Churn riski olan müşterilere özel teklif
- Win-back: Pasif müşterilere geri kazanım
- Seasonal: Dönemsel kampanyalar

A/B Test Kuralları:
- Her kampanya en az 2 varyant içermeli (A ve B)
- Varyantlar arasında tek bir değişken olmalı (ton, CTA, başlık)
- Minimum 1000 impression sonrası performans değerlendirmesi

Kurallar:
- Türkçe kampanya metni üret
- SMS: max 160 karakter
- Push: max 50 karakter
- Email: konu satırı + gövde
- Her kampanyada hedef segment belirt
"""


def _create_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="deepseek-chat",
        openai_api_base=settings.openai_api_base,
        openai_api_key=settings.openai_api_key,
        temperature=0.7,  # Higher for creative campaign text
        max_tokens=2048,
    )


def create_campaign_agent(tools=None):
    """Build the LangGraph ReAct agent with campaign tools."""
    llm = _create_llm()
    return create_react_agent(
        model=llm,
        tools=tools or ALL_TOOLS,
        prompt=SystemMessage(content=SYSTEM_PROMPT),
    )


class CampaignAgentRunner:
    """Runner for the CampaignAgent."""

    def __init__(self, use_mcp: bool = False) -> None:
        self._use_mcp = use_mcp
        self._agent = None

        if not use_mcp:
            self._agent = create_campaign_agent()

    async def _ensure_agent(self) -> None:
        if self._agent is not None:
            return

        if self._use_mcp:
            from infrastructure.mcp.client import MCPToolClient

            client = MCPToolClient(servers={"campaign": "infrastructure.mcp.campaign_mcp_server"})
            mcp_tools = await client.discover_tools()
            self._agent = create_campaign_agent(tools=mcp_tools)
            logger.info("CampaignAgent initialized with %d MCP tools", len(mcp_tools))
        else:
            self._agent = create_campaign_agent()

    async def generate_campaign(
        self,
        customer_id: str | None = None,
        target_segment: str = "gold",
        campaign_type: str = "sms",
        product: str = "",
        campaign_goal: str = "upsell",
    ) -> dict[str, Any]:
        """Generate a campaign for a target segment or specific customer."""
        session_id = str(uuid.uuid4())

        message_parts = ["Kampanya Talebi:"]
        if customer_id:
            message_parts.append(f"- Müşteri ID: {customer_id} (önce segmentini kontrol et)")
        else:
            message_parts.append(f"- Hedef Segment: {target_segment}")
        message_parts.extend(
            [
                f"- Kanal: {campaign_type}",
                f"- Ürün/Teklif: {product}",
                f"- Kampanya Amacı: {campaign_goal}",
                "",
                "Lütfen:",
                "1. Müşteri segmentini doğrula (varsa)",
                "2. Segmente uygun ton belirle",
                "3. A/B varyantlı kampanya metni üret",
            ]
        )
        message = "\n".join(message_parts)

        await self._ensure_agent()

        try:
            async with asyncio.timeout(300):
                result = await self._agent.ainvoke(
                    {"messages": [HumanMessage(content=message)]},
                    config={"configurable": {"thread_id": session_id}},
                )
        except TimeoutError:
            return {
                "session_id": session_id,
                "target_segment": target_segment,
                "campaign_type": campaign_type,
                "response": "Agent zaman aşımına uğradı.",
                "message_count": 0,
            }

        messages = result.get("messages", [])
        final_message = messages[-1].content if messages else "No response generated"

        return {
            "session_id": session_id,
            "customer_id": customer_id,
            "target_segment": target_segment,
            "campaign_type": campaign_type,
            "campaign_goal": campaign_goal,
            "response": final_message,
            "message_count": len(messages),
        }
