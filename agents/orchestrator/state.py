"""Orchestrator — Shared state definition for the multi-agent supervisor.

Defines the AgentState TypedDict used by the LangGraph supervisor graph.
All nodes (supervisor, specialist agents) read/write to this shared state.
"""

from __future__ import annotations

from typing import Annotated, Any

from langgraph.graph import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """State shared across all nodes in the supervisor graph.

    Fields:
        messages: Conversation history (accumulated via add_messages reducer)
        customer_id: Customer UUID (set by the initial event)
        domain: Routing domain decided by supervisor (billing | network | campaign | customer_support)
        tools_used: List of tool names invoked during this session
        routing_decision: Supervisor's routing rationale
        final_response: The specialist agent's final answer
        metadata: Additional context (priority, complaint_type, etc.)
    """

    messages: Annotated[list[Any], add_messages]
    customer_id: str
    domain: str
    tools_used: list[str]
    routing_decision: str
    final_response: str | None
    metadata: dict[str, Any]
