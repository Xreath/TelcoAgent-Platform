# ADR-002: LangGraph for Agent Orchestration

**Status:** Accepted
**Date:** 2026-03-01
**Decision Makers:** Fazlı Koç

## Context

The platform requires multi-agent orchestration — a supervisor agent routing to 4 specialist agents (CustomerSupport, NetworkDiagnostic, BillingAnalyst, Campaign). Options considered:

1. **LangGraph** — Graph-based agent orchestration with conditional edges
2. **AutoGen** — Multi-agent group chat paradigm
3. **LangGraph + AutoGen hybrid** — Different frameworks for different agents

## Decision

Use **LangGraph exclusively** for all agent orchestration. AutoGen deferred to a separate project (ResearchAgentLab).

## Rationale

- Single framework mastery > dual framework surface knowledge
- LangGraph's StateGraph + conditional edges naturally model supervisor → specialist routing
- ReAct pattern (create_react_agent) covers all current use cases
- Group Chat pattern can be simulated via prompt engineering within LangGraph
- Debugging and tracing is simpler with one framework (LangSmith)

## Consequences

- **Positive:** Consistent codebase, single tracing pipeline, simpler dependency tree
- **Negative:** Cannot demonstrate AutoGen's native group chat in this project
- **Mitigation:** AutoGen explored in ResearchAgentLab with dedicated scenarios
