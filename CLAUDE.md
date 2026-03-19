# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TelcoAgent Platform is an enterprise agentic AI system for telecom operations. It combines Domain-Driven Design (DDD), event-driven microservices, LangGraph multi-agent orchestration, and MCP (Model Context Protocol) into a single monorepo.

## Commands

```bash
# Install dependencies (uses uv)
uv sync
uv sync --extra dev  # includes pytest, ruff, mypy

# Run a service (example: customer service on port 8001)
uvicorn services.customer.api.main:app --reload --port 8001

# Run Orchestrator (Supervisor agent + Kafka consumer)
python -m agents.orchestrator.main

# Run CustomerSupportAgent (Kafka consumer + agent loop)
python -m agents.customer_support.main

# Run an MCP server standalone
python -m infrastructure.mcp.customer_mcp_server

# Start infrastructure (PostgreSQL, Redis, Kafka, etc.)
docker compose up -d

# Database migrations (Alembic)
alembic upgrade head                              # apply all migrations
alembic revision --autogenerate -m "description"  # generate new migration

# Tests
pytest
pytest tests/path/to/test_file.py::test_name  # single test

# Lint / format
ruff check .
ruff format .

# Type check
mypy .

# Seed mock data
python scripts/seed_mock_data.py

# Benchmark REST vs MCP
python scripts/benchmark_protocols.py
```

Line length is 120 characters (ruff, rules: E/F/I/N/W/UP). Mypy is configured in strict mode (python 3.11). pytest uses `asyncio_mode = "auto"`.

### Dev Mode

Set `DEV_MODE=true` in `.env` to bypass JWT authentication. MCP servers also fall back to mock data when their upstream REST service is unreachable.

### Service Ports

Customer `:8001`, Billing `:8002`, Network `:8003`, Campaign `:8004`, Customer Support Agent `:8010`. Kafka UI `:8082`, Traefik Dashboard `:8084`, Prometheus `:9090`, Alertmanager `:9093`, Grafana `:3000`.

## Architecture

### Monorepo Layout

```
services/<domain>/       # DDD Bounded Contexts (customer, billing, network, campaign)
agents/<name>/           # AI agents (all fully implemented)
infrastructure/          # Cross-cutting infra (MCP servers, Docker, monitoring)
shared/                  # Reusable base classes, config, database utils
```

### Bounded Context Structure (per service)

Each `services/<domain>/` follows the same layered DDD structure:

- `domain/model/` — Aggregate Root, Value Objects, Domain Events
- `domain/repository.py` — Abstract repository interface
- `domain/services.py` — Pure domain logic (no I/O)
- `application/commands/handlers.py` — CQRS write side
- `application/queries/handlers.py` — CQRS read side
- `infrastructure/` — Postgres repository, Kafka publisher (Outbox pattern), ORM models
- `api/main.py` + `api/routes.py` — FastAPI app and versioned routes (`/v1/`)

### Shared Base Classes (`shared/`)

- `shared/models/base.py` — `ValueObject`, `Entity`, `AggregateRoot` (Pydantic-based). Aggregates collect domain events via `add_event()` / `collect_events()`.
- `shared/events/base.py` — `DomainEvent` base class (frozen Pydantic model).
- `shared/config/settings.py` — `Settings` (pydantic-settings, reads from `.env`). Always use `get_settings()` (LRU-cached singleton).
- `shared/utils/database.py` — SQLAlchemy async engine and `get_db_session()` FastAPI dependency.

### Agent Architecture (`agents/`)

All 5 agents are fully implemented using LangGraph:

- **Orchestrator** (`agents/orchestrator/`) — LangGraph StateGraph Supervisor. Routes incoming events to the correct specialist via conditional edges. Keyword-based domain classification with JSON fallback. Produces decisions to `telco.agents.decisions`.
- **CustomerSupportAgent** (`agents/customer_support/`) — LangGraph ReAct. Reference implementation with Redis memory, Prometheus metrics, Kafka consumer. Tools: `get_customer_profile`, `get_billing_info`, `create_ticket`, `send_notification`.
- **BillingAnalystAgent** (`agents/billing_analyst/`) — LangGraph ReAct with Structured Output. Dispute resolution (approve/reject/partial_refund), anomaly detection.
- **NetworkDiagnosticAgent** (`agents/network_diagnostic/`) — LangGraph ReAct. System prompt simulates 3 personas (Analyst, Engineer, Manager) for multi-perspective diagnosis.
- **CampaignAgent** (`agents/campaign/`) — LangGraph ReAct. Segment-targeted content generation, A/B variant creation.

Each agent has `agent.py` (LangGraph agent + Runner class) and `tools.py` (LangChain tools). Agents support two tool modes: static tools (default) or dynamic MCP tool discovery.

### Domain Model Pattern: Pending Complaints

The Customer aggregate uses `_pending_complaints` (same copy+clear pattern as `_pending_events`). `file_complaint()` adds to `_pending_complaints`; `collect_complaints()` returns and clears. Command handler must call `collect_complaints()` after save to persist complaints to DB.

### MCP Layer (`infrastructure/mcp/`)

- 4 FastMCP servers: `customer_mcp_server.py`, `billing_mcp_server.py`, `campaign_mcp_server.py`, `network_mcp_server.py`. Each connects to the corresponding REST service. Falls back to mock data when the service is unreachable.
- `client.py` — `MCPToolClient` that discovers tools from configured MCP server URLs and returns LangChain-compatible tool objects.
- `openapi_to_mcp.py` — Auto-generates MCP tool definitions from OpenAPI schemas.

### Event Flow (Outbox Pattern)

1. Command handler calls aggregate method → aggregate raises a `DomainEvent` internally.
2. Handler saves the entity **and** calls `OutboxRepository.save(event)` in the same DB transaction.
3. `OutboxPoller.poll_and_publish()` reads unpublished events from `outbox.events` and sends them to Kafka, then marks them published.

Kafka topic namespace: `telco.customers.*`, `telco.billing.*`, `telco.network.*`, `telco.campaigns.*`, `telco.agents.decisions`, `telco.dlq.*`.

Retry: exponential backoff (`base_delay * 2^(attempt-1)`, max 3 retries). Deserialization errors bypass retry → straight to DLQ.

### LLM Configuration

Uses DeepSeek API (OpenAI-compatible). Set `OPENAI_API_BASE=https://api.deepseek.com/v1` and `OPENAI_API_KEY` in `.env`. The model name in code is `"deepseek-chat"`. LangSmith tracing is enabled by default when `LANGCHAIN_API_KEY` is set.

### Infrastructure (Docker Compose)

Copy `.env.example` to `.env`. `docker compose up -d` starts:

- **Data**: PostgreSQL+pgvector (`:5432`), Redis (`:6379`), Kafka+ZooKeeper (`:9092`)
- **Services**: customer-service, billing-service, network-service, campaign-service, customer-support-agent
- **Gateway**: Traefik v3.2 (`:8084` dashboard) — API routing + service discovery
- **Monitoring**: Prometheus (`:9090`), Alertmanager (`:9093`), Grafana (`:3000`)
- **Tools**: Kafka UI (`:8082`)

DB migrations are managed by Alembic (migration files in `alembic/versions/`). The `infrastructure/docker/init-db.sql` sets up the `outbox.events` table and pgvector extension.

### Security

- **Auth**: Self-contained JWT (HS256) with RBAC (`agent-operator`, `agent-supervisor`, `agent-auditor`). Middleware in `shared/auth/middleware.py`. Use `create_access_token()` to issue tokens. No external identity provider.
- **Prompt Injection Guard** (`shared/security/`): Scans user text for injection patterns (role hijacking, system prompt extraction, delimiter injection, tool manipulation). HIGH-risk → blocked, MEDIUM-risk → redacted. Supports English and Turkish.
- **Input Sanitization**: 2000-char limit on user-controlled fields before LLM processing.
