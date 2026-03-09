"""BillingAnalystAgent — LangGraph agent with Structured Output for billing analysis.

Architecture:
  - LangGraph ReAct agent with structured output for dispute decisions
  - Specializes in invoice anomaly detection, explanation, and dispute resolution
  - DeepSeek API (OpenAI-compatible) as LLM backend
  - CQRS-aware: reads from query side, writes via command side

Flow:
  1. Billing anomaly or dispute event arrives
  2. Agent fetches invoice details and runs anomaly detection
  3. Agent generates customer-friendly explanation
  4. Agent processes dispute with structured decision (approve/reject/partial)
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from agents.billing_analyst.tools import ALL_TOOLS
from shared.config.settings import get_settings
from shared.security import PromptInjectionError, sanitize_input

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """Sen TelcoAgent platformunun Fatura Analiz Uzmanısın (BillingAnalystAgent).

Görevin:
1. Fatura anomalilerini tespit etmek (detect_anomaly)
2. Fatura detaylarını incelemek (get_invoice_detail)
3. Müşteriye açıklama üretmek (generate_explanation)
4. İtirazları çözmek (process_dispute)

Analiz Süreci:
1. Önce müşterinin fatura geçmişini kontrol et (detect_anomaly)
2. Anomali varsa, ilgili faturanın detayına bak (get_invoice_detail)
3. Line item bazlı analiz yap: hangi kalem normal dışı?
4. Müşteriye anlaşılır açıklama üret (generate_explanation)
5. İtiraz varsa karar ver:
   - Haklı itiraz (anormal artış, hizmet dışı ücret) → approve_refund
   - Kısmi haklı (bazı kalemler tartışmalı) → partial_refund
   - Geçerli ücretlendirme → reject (nazik bir dille)

Karar Kriterleri:
- %30+ sapma VE açıklanamayan line item → approve_refund
- %30+ sapma AMA açıklanabilir (roaming, ek paket) → reject + explanation
- Belirli bir kalem hatalı → partial_refund (sadece o kalem kadar)
- Müşteri segmenti gold/platinum ise → retention odaklı karar (iade eğilimli)

Structured Output:
Her karar sonunda şu yapıda özet ver:
- decision: approve_refund | reject | partial_refund
- confidence: 0.0-1.0
- reason: Kısa açıklama

Kurallar:
- Türkçe yanıt ver, profesyonel ol
- Her adımda hangi tool'u neden kullandığını belirt
- Müşteri memnuniyetini ön planda tut
"""


def _create_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="deepseek-chat",
        openai_api_base=settings.openai_api_base,
        openai_api_key=settings.openai_api_key,
        temperature=0.1,
        max_tokens=2048,
    )


def create_billing_analyst_agent(tools=None):
    """Build the LangGraph ReAct agent with billing analysis tools."""
    llm = _create_llm()
    return create_react_agent(
        model=llm,
        tools=tools or ALL_TOOLS,
        prompt=SystemMessage(content=SYSTEM_PROMPT),
    )


class BillingAnalystAgentRunner:
    """Runner for the BillingAnalystAgent."""

    def __init__(self, use_mcp: bool = False) -> None:
        self._use_mcp = use_mcp
        self._agent = None

        if not use_mcp:
            self._agent = create_billing_analyst_agent()

    async def _ensure_agent(self) -> None:
        if self._agent is not None:
            return

        if self._use_mcp:
            from infrastructure.mcp.client import MCPToolClient

            client = MCPToolClient(servers={"billing": "infrastructure.mcp.billing_mcp_server"})
            mcp_tools = await client.discover_tools()
            from agents.billing_analyst.tools import generate_explanation, process_dispute

            all_tools = mcp_tools + [generate_explanation, process_dispute]
            self._agent = create_billing_analyst_agent(tools=all_tools)
            logger.info("BillingAnalystAgent initialized with %d MCP tools + 2 static tools", len(mcp_tools))
        else:
            self._agent = create_billing_analyst_agent()

    async def handle_dispute(
        self,
        customer_id: str,
        invoice_id: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """Process a billing dispute end-to-end."""
        session_id = str(uuid.uuid4())

        # Sanitize user-controlled input
        try:
            reason = sanitize_input(reason, field_name="dispute_reason")
        except PromptInjectionError as e:
            logger.error("Prompt injection in dispute from customer %s: %s", customer_id, e)
            return {
                "session_id": session_id,
                "customer_id": customer_id,
                "invoice_id": invoice_id,
                "response": "İtiraz içeriği güvenlik kontrolünden geçemedi.",
                "message_count": 0,
            }

        message = (
            f"Fatura İtirazı:\n"
            f"- Müşteri ID: {customer_id}\n"
            f"- Fatura ID: {invoice_id}\n"
            f"- İtiraz Nedeni: {reason}\n\n"
            f"Lütfen şu adımları takip et:\n"
            f"1. Müşterinin fatura geçmişini analiz et (detect_anomaly)\n"
            f"2. İlgili faturanın detayını incele (get_invoice_detail)\n"
            f"3. Müşteriye açıklama üret (generate_explanation)\n"
            f"4. İtirazı karara bağla (process_dispute)"
        )

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
                "customer_id": customer_id,
                "invoice_id": invoice_id,
                "response": "Agent zaman aşımına uğradı.",
                "message_count": 0,
            }

        messages = result.get("messages", [])
        final_message = messages[-1].content if messages else "No response generated"

        return {
            "session_id": session_id,
            "customer_id": customer_id,
            "invoice_id": invoice_id,
            "response": final_message,
            "message_count": len(messages),
        }

    async def handle_anomaly(
        self,
        customer_id: str,
        anomaly_type: str = "billing_spike",
        description: str = "",
    ) -> dict[str, Any]:
        """Process a billing anomaly detection event."""
        session_id = str(uuid.uuid4())

        # Sanitize user-controlled input
        try:
            description = sanitize_input(description, field_name="anomaly_description")
        except PromptInjectionError as e:
            logger.error("Prompt injection in anomaly from customer %s: %s", customer_id, e)
            return {
                "session_id": session_id,
                "customer_id": customer_id,
                "anomaly_type": anomaly_type,
                "response": "Anomali açıklaması güvenlik kontrolünden geçemedi.",
                "message_count": 0,
            }

        message = (
            f"Fatura Anomali Tespiti:\n"
            f"- Müşteri ID: {customer_id}\n"
            f"- Anomali Tipi: {anomaly_type}\n"
            f"- Açıklama: {description}\n\n"
            f"Lütfen anomaliyi analiz et ve müşteriye açıklama hazırla."
        )

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
                "customer_id": customer_id,
                "anomaly_type": anomaly_type,
                "response": "Agent zaman aşımına uğradı.",
                "message_count": 0,
            }

        messages = result.get("messages", [])
        final_message = messages[-1].content if messages else "No response generated"

        return {
            "session_id": session_id,
            "customer_id": customer_id,
            "anomaly_type": anomaly_type,
            "response": final_message,
            "message_count": len(messages),
        }
