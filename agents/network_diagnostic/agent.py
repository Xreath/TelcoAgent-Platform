"""NetworkDiagnosticAgent — AutoGen-style Group Chat agent for network fault diagnosis.

Architecture:
  - Uses AG2 (AutoGen) ConversableAgent for multi-persona group chat simulation
  - Three personas: Analyst (root-cause), Engineer (diagnostics), Manager (escalation)
  - Falls back to LangGraph ReAct if AG2 is not available
  - DeepSeek API (OpenAI-compatible) as LLM backend

Flow:
  1. Network anomaly event arrives (Kafka or manual trigger)
  2. Analyst persona identifies potential root causes
  3. Engineer persona runs diagnostic tools
  4. Manager persona decides on escalation
  5. Final report is generated
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from agents.network_diagnostic.tools import ALL_TOOLS
from shared.config.settings import get_settings
from shared.security import PromptInjectionError, sanitize_input

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """Sen TelcoAgent platformunun Ağ Teşhis Uzmanısın (NetworkDiagnosticAgent).

Görevin:
1. Ağ anomalilerini ve arızalarını tespit etmek
2. Etkilenen düğümleri belirlemek (query_network_topology)
3. Teşhis testleri çalıştırmak (run_diagnostic_script)
4. Ciddi sorunları operasyon ekibine eskale etmek (escalate_to_ops)

Çalışma Yöntemi (Group Chat Simülasyonu):
Sen üç farklı perspektiften analiz yaparsın:

[ANALYST] — Kök neden analizi:
- Anomali verilerini incele, olası kök nedenleri sırala
- Benzer geçmiş olayları düşün

[ENGINEER] — Teknik teşhis:
- Uygun teşhis testlerini çalıştır (ping, traceroute, bandwidth, full)
- Sonuçları yorumla, darboğazları bul

[MANAGER] — Karar ve eskalasyon:
- Etki analizini yap (kaç müşteri etkileniyor?)
- Eskalasyon kararı ver (severity: critical/high/medium/low)
- SLA takibi

Kurallar:
- Her zaman önce topology'yi sorgula
- Degraded/down düğümlere teşhis çalıştır
- Paket kaybı > 2% veya latency > 100ms ise HIGH severity
- Tam kesinti (down) ise CRITICAL severity
- Her eskalasyonda özet rapor yaz
- Türkçe yanıt ver, teknik terimler İngilizce kalabilir
"""


def _create_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="deepseek-chat",
        openai_api_base=settings.openai_api_base,
        openai_api_key=settings.openai_api_key,
        temperature=0.1,
        max_tokens=2048,
    )


def create_network_diagnostic_agent(tools=None):
    """Build the LangGraph ReAct agent with network diagnostic tools."""
    llm = _create_llm()
    return create_react_agent(
        model=llm,
        tools=tools or ALL_TOOLS,
        prompt=SystemMessage(content=SYSTEM_PROMPT),
    )


class NetworkDiagnosticAgentRunner:
    """Runner for the NetworkDiagnosticAgent.

    Wraps the LangGraph agent and provides a high-level API for handling
    network anomaly events.
    """

    def __init__(self, use_mcp: bool = False) -> None:
        self._use_mcp = use_mcp
        self._agent = None

        if not use_mcp:
            self._agent = create_network_diagnostic_agent()

    async def _ensure_agent(self) -> None:
        if self._agent is not None:
            return

        if self._use_mcp:
            from infrastructure.mcp.client import MCPToolClient

            client = MCPToolClient(servers={"network": "infrastructure.mcp.network_mcp_server"})
            mcp_tools = await client.discover_tools()
            self._agent = create_network_diagnostic_agent(tools=mcp_tools)
            logger.info("NetworkDiagnosticAgent initialized with %d MCP tools", len(mcp_tools))
        else:
            self._agent = create_network_diagnostic_agent()

    async def handle_anomaly(
        self,
        node_id: str | None = None,
        region: str | None = None,
        anomaly_type: str = "performance_degradation",
        description: str = "",
        severity: str = "medium",
    ) -> dict[str, Any]:
        """Process a network anomaly event end-to-end."""
        session_id = str(uuid.uuid4())

        # Sanitize user-controlled input
        try:
            description = sanitize_input(description, field_name="network_anomaly_description")
        except PromptInjectionError as e:
            logger.error("Prompt injection in network anomaly: %s", e)
            return {
                "session_id": session_id,
                "node_id": node_id,
                "anomaly_type": anomaly_type,
                "response": "Anomali açıklaması güvenlik kontrolünden geçemedi.",
                "message_count": 0,
            }

        message = (
            f"Ağ Anomali Raporu:\n"
            f"- Düğüm ID: {node_id or 'Bilinmiyor — tüm bölgeyi tara'}\n"
            f"- Bölge: {region or 'Belirtilmemiş'}\n"
            f"- Anomali Tipi: {anomaly_type}\n"
            f"- Severity: {severity}\n"
            f"- Açıklama: {description}\n\n"
            f"Lütfen [ANALYST], [ENGINEER] ve [MANAGER] perspektiflerinden analiz yap.\n"
            f"1. Topology'yi sorgula ve etkilenen düğümleri bul\n"
            f"2. Sorunlu düğümlere teşhis çalıştır\n"
            f"3. Gerekirse operasyon ekibine eskale et"
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
                "node_id": node_id,
                "anomaly_type": anomaly_type,
                "response": "Agent zaman aşımına uğradı.",
                "message_count": 0,
            }

        messages = result.get("messages", [])
        final_message = messages[-1].content if messages else "No response generated"

        return {
            "session_id": session_id,
            "node_id": node_id,
            "region": region,
            "anomaly_type": anomaly_type,
            "severity": severity,
            "response": final_message,
            "message_count": len(messages),
        }
