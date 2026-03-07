"""CustomerSupportAgent — LangGraph ReAct agent for complaint handling.

Architecture:
  - LangGraph create_react_agent with tools (static + MCP dynamic)
  - DeepSeek API (OpenAI-compatible) as LLM backend
  - Redis short-term memory for conversation context
  - LangSmith tracing for observability
  - Prometheus metrics for latency/token tracking

Tool modes:
  - Static: hardcoded tools from agents/customer_support/tools.py
  - MCP Dynamic: tools discovered at runtime from MCP servers (no agent restart needed)

Flow:
  1. Kafka consumer receives ComplaintFiled event
  2. Agent fetches customer profile + billing info (via MCP or static tools)
  3. Agent analyzes complaint and decides resolution
  4. Agent creates ticket + sends notification
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from agents.customer_support.memory import RedisMemory
from agents.customer_support.metrics import AgentMetrics
from agents.customer_support.tools import ALL_TOOLS
from shared.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── LangSmith tracing ────────────────────────────────────────
os.environ.setdefault("LANGCHAIN_TRACING_V2", str(settings.langchain_tracing_v2).lower())
os.environ.setdefault("LANGCHAIN_API_KEY", settings.langchain_api_key)
os.environ.setdefault("LANGCHAIN_PROJECT", settings.langchain_project)

# ── System prompt ─────────────────────────────────────────────
SYSTEM_PROMPT = """Sen TelcoAgent platformunun Müşteri Destek Uzmanısın.

Görevin:
1. Müşteri şikayetlerini analiz etmek
2. Müşteri profilini ve fatura geçmişini incelemek
3. Uygun çözüm üretmek
4. Ticket oluşturmak ve müşteriyi bilgilendirmek

Kurallar:
- Her zaman önce müşteri profilini çek (get_customer_profile)
- Fatura şikayetlerinde mutlaka fatura bilgilerini kontrol et (get_billing_info)
- Her çözümde ticket oluştur (create_ticket)
- Her ticket sonrası müşteriyi bilgilendir (send_notification)
- Gold ve platinum segmentteki müşterilere öncelik ver
- Türkçe yanıt ver, profesyonel ve empatik ol

Öncelik Kuralları:
- critical: 1 saat içinde çözüm, üst düzey yöneticiye eskalasyon
- high: 4 saat içinde çözüm
- medium: 24 saat içinde çözüm
- low: 48 saat içinde çözüm
"""


def _create_llm() -> ChatOpenAI:
    """Create the LLM instance (DeepSeek, OpenAI-compatible)."""
    return ChatOpenAI(
        model="deepseek-chat",
        openai_api_base=settings.openai_api_base,
        openai_api_key=settings.openai_api_key,
        temperature=0.1,
        max_tokens=2048,
    )


def create_customer_support_agent(tools=None):
    """Build the LangGraph ReAct agent with tools and system prompt."""
    llm = _create_llm()
    agent = create_react_agent(
        model=llm,
        tools=tools or ALL_TOOLS,
        prompt=SystemMessage(content=SYSTEM_PROMPT),
    )
    return agent


class CustomerSupportAgentRunner:
    """High-level runner that wraps the LangGraph agent with memory + metrics.

    Supports two modes:
    - use_mcp=False (default): uses static tools from tools.py
    - use_mcp=True: discovers tools from MCP servers at runtime
    """

    def __init__(self, use_mcp: bool = False) -> None:
        self._use_mcp = use_mcp
        self._agent = None  # lazy init when MCP
        self._memory = RedisMemory()
        self._metrics = AgentMetrics()

        if not use_mcp:
            self._agent = create_customer_support_agent()

    async def _ensure_agent(self) -> None:
        """Ensure agent is initialized, discovering MCP tools if needed."""
        if self._agent is not None:
            return

        if self._use_mcp:
            from infrastructure.mcp.client import MCPToolClient

            client = MCPToolClient()
            mcp_tools = await client.discover_tools()
            # Combine MCP tools with static tools (create_ticket, send_notification)
            from agents.customer_support.tools import create_ticket, send_notification

            all_tools = mcp_tools + [create_ticket, send_notification]
            self._agent = create_customer_support_agent(tools=all_tools)
            logger.info("Agent initialized with %d MCP tools + 2 static tools", len(mcp_tools))
        else:
            self._agent = create_customer_support_agent()

    async def handle_complaint(
        self,
        customer_id: str,
        complaint_type: str,
        description: str,
        priority: str = "medium",
    ) -> dict[str, Any]:
        """Process a customer complaint end-to-end.

        Returns the agent's final response and metadata.
        """
        session_id = str(uuid.uuid4())

        # Store session metadata in Redis
        await self._memory.set_metadata(
            session_id,
            customer_id=customer_id,
            complaint_type=complaint_type,
            priority=priority,
        )

        # Build the complaint message for the agent
        complaint_message = (
            f"Müşteri Şikayeti:\n"
            f"- Müşteri ID: {customer_id}\n"
            f"- Şikayet Tipi: {complaint_type}\n"
            f"- Öncelik: {priority}\n"
            f"- Açıklama: {description}\n\n"
            f"Lütfen bu şikayeti analiz et ve çöz."
        )

        # Ensure agent is ready (discovers MCP tools on first call)
        await self._ensure_agent()

        # Save to memory
        await self._memory.add_message(session_id, "user", complaint_message)

        # Run agent with metrics tracking and timeout
        with self._metrics.track_invocation(complaint_type, priority):
            try:
                async with asyncio.timeout(300):  # 5 minute timeout
                    result = await self._agent.ainvoke(
                        {"messages": [HumanMessage(content=complaint_message)]},
                        config={"configurable": {"thread_id": session_id}},
                    )
            except TimeoutError:
                self._metrics.track_error("timeout")
                return {
                    "session_id": session_id,
                    "customer_id": customer_id,
                    "complaint_type": complaint_type,
                    "priority": priority,
                    "response": "Agent zaman asimina ugradi. Lutfen tekrar deneyin.",
                    "message_count": 0,
                }

        # Extract final response
        messages = result.get("messages", [])
        final_message = messages[-1].content if messages else "No response generated"

        # Track tool calls (including errors from ToolMessages)
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    self._metrics.track_tool_call(tc["name"])
            if msg.type == "tool" and hasattr(msg, "status") and msg.status == "error":
                self._metrics.track_error(f"tool_{msg.name}")

        # Save response to memory
        await self._memory.add_message(session_id, "assistant", final_message)

        return {
            "session_id": session_id,
            "customer_id": customer_id,
            "complaint_type": complaint_type,
            "priority": priority,
            "response": final_message,
            "message_count": len(messages),
        }

    async def close(self) -> None:
        """Cleanup resources."""
        await self._memory.close()
