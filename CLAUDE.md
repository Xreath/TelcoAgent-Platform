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

Line length is 120 characters (ruff). Mypy is configured in strict mode. pytest uses `asyncio_mode = "auto"`.

### Dev Mode

Set `DEV_MODE=true` in `.env` to bypass JWT authentication. MCP servers also fall back to mock data when their upstream REST service is unreachable.

### Service Ports

Customer `:8001`, Billing `:8002`, Network `:8003`, Campaign `:8004`. Kafka UI `:8082`, Prometheus `:9090`, Grafana `:3000`.

## Architecture

### Monorepo Layout

```
services/<domain>/       # DDD Bounded Contexts (customer, billing, network, campaign)
agents/<name>/           # AI agents (customer_support implemented; others stubbed)
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

### Agent Structure (`agents/<name>/`)

The CustomerSupportAgent is the reference implementation:

- `agent.py` — LangGraph `create_react_agent` with a system prompt; `CustomerSupportAgentRunner` wraps it with memory + metrics, supporting two modes: static tools (default) or dynamic MCP tool discovery.
- `tools.py` — Static LangChain tools (`get_customer_profile`, `get_billing_info`, `create_ticket`, `send_notification`).
- `memory.py` — Redis-backed short-term memory per session.
- `metrics.py` — Prometheus counters/histograms for invocations and tool calls.
- `kafka_consumer.py` — Consumes `telco.customers.complaints` topic and dispatches to the agent.
- `main.py` — Entry point that starts the Kafka consumer loop.

### MCP Layer (`infrastructure/mcp/`)

- `customer_mcp_server.py` / `billing_mcp_server.py` — FastMCP servers exposing domain tools. Each connects to the corresponding REST service. Fall back to mock data when the service is unreachable (dev mode).
- `client.py` — `MCPToolClient` that discovers tools from configured MCP server URLs and returns LangChain-compatible tool objects.
- `openapi_to_mcp.py` — Auto-generates MCP tool definitions from OpenAPI schemas.

### Event Flow (Outbox Pattern)

1. Command handler calls aggregate method → aggregate raises a `DomainEvent` internally.
2. Handler saves the entity **and** calls `OutboxRepository.save(event)` in the same DB transaction.
3. `OutboxPoller.poll_and_publish()` reads unpublished events from `outbox.events` and sends them to Kafka, then marks them published.

Kafka topic namespace: `telco.customers.*`, `telco.billing.*`, `telco.network.*`, `telco.campaigns.*`, `telco.agents.decisions`, `telco.dlq.*`.

### LLM Configuration

Uses DeepSeek API (OpenAI-compatible). Set `OPENAI_API_BASE=https://api.deepseek.com/v1` and `OPENAI_API_KEY` in `.env`. The model name in code is `"deepseek-chat"`. LangSmith tracing is enabled by default when `LANGCHAIN_API_KEY` is set.

### Infrastructure Dependencies (local dev)

Copy `.env.example` to `.env`. Services expect:

- PostgreSQL on `localhost:5432` (db: `telcoagent`, user: `telco`)
- Redis on `localhost:6379`
- Kafka on `localhost:9092`

DB migrations are managed by Alembic (migration files in `alembic/versions/`). The `infrastructure/docker/init-db.sql` sets up the `outbox.events` table and pgvector extension.

### Security

- **Auth**: Simple JWT (HS256) with RBAC (`agent-operator`, `agent-supervisor`, `agent-auditor`). Middleware in `shared/auth/middleware.py`. Use `create_access_token()` to issue tokens.
- **Prompt Injection Guard** (`shared/security/`): Scans user text for injection patterns (role hijacking, system prompt extraction, delimiter injection, tool manipulation). HIGH-risk → blocked, MEDIUM-risk → redacted. Supports English and Turkish.
- **Input Sanitization**: 2000-char limit on user-controlled fields before LLM processing.
