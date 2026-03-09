"""Orchestrator — LangGraph Supervisor Agent with conditional routing.

Architecture:
  - LangGraph StateGraph with supervisor node + specialist agent nodes
  - Supervisor analyzes incoming request and routes to the correct specialist
  - Conditional edges based on domain classification
  - Each specialist agent runs as a sub-graph node
  - Agent-to-agent communication via shared state

Graph Structure:
  START → supervisor → (conditional edge) → specialist_agent → END

Routing Logic:
  - billing keywords → BillingAnalystAgent
  - network keywords → NetworkDiagnosticAgent
  - campaign keywords → CampaignAgent
  - default → CustomerSupportAgent
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from agents.orchestrator.state import AgentState
from shared.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SUPERVISOR_SYSTEM_PROMPT = """Sen TelcoAgent platformunun Supervisor Agent'ısın (Orkestratör).

Görevin gelen talepleri analiz edip doğru uzman agenta yönlendirmektir.

Uzman Agentlar:
1. customer_support — Müşteri şikayetleri, genel destek, ticket oluşturma
2. billing — Fatura anomalileri, itirazlar, ödeme sorunları
3. network — Ağ arızaları, bağlantı sorunları, performans düşüşü
4. campaign — Kampanya oluşturma, segment bazlı teklif, A/B test

Yönlendirme Kuralları:
- Fatura, ücret, ödeme, iade, itiraz → billing
- Ağ, bağlantı, sinyal, hız, kesinti, baz istasyonu → network
- Kampanya, teklif, promosyon, indirim, segment, churn → campaign
- Şikayet, destek, genel → customer_support
- Birden fazla domain'e dokunuyorsa → en baskın olanı seç, diğerini metadata'ya not et

ÖNEMLI: Yanıtını SADECE şu JSON formatında ver, başka bir şey yazma:
{"domain": "<domain_name>", "reasoning": "<kısa açıklama>", "priority": "<low|medium|high|critical>"}
"""


def _create_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="deepseek-chat",
        openai_api_base=settings.openai_api_base,
        openai_api_key=settings.openai_api_key,
        temperature=0.0,
        max_tokens=256,
    )


def _supervisor_node(state: AgentState) -> dict[str, Any]:
    """Supervisor node: classifies the request and decides routing."""
    llm = _create_llm()

    messages = state.get("messages", [])
    if not messages:
        return {
            "domain": "customer_support",
            "routing_decision": "Mesaj yok, varsayılan yönlendirme",
        }

    response = llm.invoke([SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT)] + messages)
    content = response.content.strip()

    # Parse JSON response
    try:
        # Handle markdown code blocks
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        decision = json.loads(content)
        domain = decision.get("domain", "customer_support")
        reasoning = decision.get("reasoning", "")
        priority = decision.get("priority", "medium")
    except (json.JSONDecodeError, IndexError):
        # Fallback: keyword-based routing
        text = " ".join(m.content for m in messages if hasattr(m, "content")).lower()
        if any(kw in text for kw in ["fatura", "ödeme", "ücret", "iade", "itiraz", "billing", "invoice"]):
            domain = "billing"
            reasoning = "Keyword-based: fatura/ödeme terimleri tespit edildi"
        elif any(kw in text for kw in ["ağ", "network", "sinyal", "bağlantı", "kesinti", "hız", "bts"]):
            domain = "network"
            reasoning = "Keyword-based: ağ/network terimleri tespit edildi"
        elif any(kw in text for kw in ["kampanya", "teklif", "promosyon", "campaign", "segment", "churn"]):
            domain = "campaign"
            reasoning = "Keyword-based: kampanya terimleri tespit edildi"
        else:
            domain = "customer_support"
            reasoning = "Keyword-based: genel destek"
        priority = "medium"

    logger.info("Supervisor routing: domain=%s, reasoning=%s", domain, reasoning)

    return {
        "domain": domain,
        "routing_decision": reasoning,
        "metadata": {**state.get("metadata", {}), "priority": priority},
    }


async def _customer_support_node(state: AgentState) -> dict[str, Any]:
    """Run CustomerSupportAgent on the request."""
    from agents.customer_support.agent import CustomerSupportAgentRunner

    runner = CustomerSupportAgentRunner()
    try:
        messages = state.get("messages", [])
        user_message = messages[-1].content if messages else ""
        customer_id = state.get("customer_id", "unknown")
        metadata = state.get("metadata", {})

        result = await runner.handle_complaint(
            customer_id=customer_id,
            complaint_type=metadata.get("complaint_type", "general"),
            description=user_message,
            priority=metadata.get("priority", "medium"),
        )
        return {
            "final_response": result["response"],
            "messages": [AIMessage(content=result["response"])],
            "tools_used": state.get("tools_used", []) + ["customer_support_agent"],
        }
    finally:
        await runner.close()


async def _billing_node(state: AgentState) -> dict[str, Any]:
    """Run BillingAnalystAgent on the request."""
    from agents.billing_analyst.agent import BillingAnalystAgentRunner

    runner = BillingAnalystAgentRunner()
    messages = state.get("messages", [])
    user_message = messages[-1].content if messages else ""
    customer_id = state.get("customer_id", "unknown")
    metadata = state.get("metadata", {})

    result = await runner.handle_dispute(
        customer_id=customer_id,
        invoice_id=metadata.get("invoice_id", "unknown"),
        reason=user_message,
    )
    return {
        "final_response": result["response"],
        "messages": [AIMessage(content=result["response"])],
        "tools_used": state.get("tools_used", []) + ["billing_analyst_agent"],
    }


async def _network_node(state: AgentState) -> dict[str, Any]:
    """Run NetworkDiagnosticAgent on the request."""
    from agents.network_diagnostic.agent import NetworkDiagnosticAgentRunner

    runner = NetworkDiagnosticAgentRunner()
    messages = state.get("messages", [])
    user_message = messages[-1].content if messages else ""
    metadata = state.get("metadata", {})

    result = await runner.handle_anomaly(
        node_id=metadata.get("node_id"),
        region=metadata.get("region"),
        anomaly_type=metadata.get("anomaly_type", "performance_degradation"),
        description=user_message,
        severity=metadata.get("priority", "medium"),
    )
    return {
        "final_response": result["response"],
        "messages": [AIMessage(content=result["response"])],
        "tools_used": state.get("tools_used", []) + ["network_diagnostic_agent"],
    }


async def _campaign_node(state: AgentState) -> dict[str, Any]:
    """Run CampaignAgent on the request."""
    from agents.campaign.agent import CampaignAgentRunner

    runner = CampaignAgentRunner()
    messages = state.get("messages", [])
    user_message = messages[-1].content if messages else ""
    customer_id = state.get("customer_id", "unknown")
    metadata = state.get("metadata", {})

    result = await runner.generate_campaign(
        customer_id=customer_id if customer_id != "unknown" else None,
        target_segment=metadata.get("target_segment", "gold"),
        campaign_type=metadata.get("campaign_type", "sms"),
        product=metadata.get("product", user_message[:100]),
        campaign_goal=metadata.get("campaign_goal", "upsell"),
    )
    return {
        "final_response": result["response"],
        "messages": [AIMessage(content=result["response"])],
        "tools_used": state.get("tools_used", []) + ["campaign_agent"],
    }


def _route_to_specialist(state: AgentState) -> str:
    """Conditional edge: route to the correct specialist based on supervisor's decision."""
    domain = state.get("domain", "customer_support")
    valid_domains = {"customer_support", "billing", "network", "campaign"}
    if domain not in valid_domains:
        logger.warning("Unknown domain '%s', falling back to customer_support", domain)
        return "customer_support"
    return domain


def create_supervisor_graph() -> StateGraph:
    """Build the supervisor LangGraph with conditional routing.

    Graph:
        START → supervisor → (conditional) → specialist → END
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("supervisor", _supervisor_node)
    graph.add_node("customer_support", _customer_support_node)
    graph.add_node("billing", _billing_node)
    graph.add_node("network", _network_node)
    graph.add_node("campaign", _campaign_node)

    # Entry point
    graph.set_entry_point("supervisor")

    # Conditional edges from supervisor to specialists
    graph.add_conditional_edges(
        "supervisor",
        _route_to_specialist,
        {
            "customer_support": "customer_support",
            "billing": "billing",
            "network": "network",
            "campaign": "campaign",
        },
    )

    # All specialists go to END
    graph.add_edge("customer_support", END)
    graph.add_edge("billing", END)
    graph.add_edge("network", END)
    graph.add_edge("campaign", END)

    return graph


# Compiled graph — ready to invoke
supervisor_graph = create_supervisor_graph().compile()
