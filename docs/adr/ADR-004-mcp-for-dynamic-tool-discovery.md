# ADR-004: MCP for Dynamic Tool Discovery

**Status:** Accepted
**Date:** 2026-03-01
**Decision Makers:** Fazlı Koç

## Context

Agents need access to domain service capabilities (get customer profile, create invoice, run diagnostics). Two approaches:

1. **Static tools** — Hard-coded LangChain tool definitions per agent
2. **MCP (Model Context Protocol)** — Each domain exposes tools via a FastMCP server; agents discover tools dynamically at runtime

## Decision

Support **both modes** — static tools as default, MCP-based dynamic discovery as an opt-in mode.

## Rationale

- **MCP enables zero-restart tool updates:** New domain capabilities are exposed without redeploying agents
- **Protocol standard:** MCP is becoming a standard for LLM tool exposure (Anthropic-backed)
- **Static fallback:** For testing and local dev, static tools are simpler and faster
- **Auto-generation:** `openapi_to_mcp.py` generates MCP tool definitions from existing OpenAPI schemas

## Implementation

- 4 FastMCP servers: customer, billing, network, campaign
- `MCPToolClient` discovers tools from configured server URLs
- `CustomerSupportAgentRunner(use_mcp=True)` activates dynamic mode
- Each MCP server falls back to mock data when its domain service is unreachable

## Consequences

- **Positive:** Decoupled agent-service evolution, aligns with industry direction
- **Negative:** Extra network hop (agent → MCP server → domain service), more moving parts
- **Mitigation:** MCP servers are lightweight, colocated with domain services
