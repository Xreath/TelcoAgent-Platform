# TelcoAgent Platform

Enterprise Agentic AI Platform for Telecom Operations — combining Domain-Driven Design, event-driven microservices, LangGraph multi-agent orchestration, and Model Context Protocol (MCP) in a single monorepo.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway (Traefik)                     │
└──────────┬──────────┬──────────┬──────────┬─────────────────────┘
           │          │          │          │
     ┌─────▼───┐ ┌───▼────┐ ┌──▼────┐ ┌──▼──────┐
     │Customer │ │Billing │ │Network│ │Campaign │   Domain Services
     │ :8001   │ │ :8002  │ │ :8003 │ │ :8004   │   (FastAPI + DDD)
     └────┬────┘ └───┬────┘ └──┬────┘ └──┬──────┘
          │          │         │          │
          ▼          ▼         ▼          ▼
   ┌──────────────────────────────────────────┐
   │          PostgreSQL (Outbox Pattern)      │
   │          + pgvector extension             │
   └──────────────────┬───────────────────────┘
                      │ poll & publish
                      ▼
   ┌──────────────────────────────────────────┐
   │              Apache Kafka                 │
   │    telco.customers.* / telco.billing.*    │
   │    telco.network.* / telco.campaigns.*    │
   └──────────────────┬───────────────────────┘
                      │ consume
                      ▼
   ┌──────────────────────────────────────────┐
   │         Orchestrator (Supervisor)         │
   │         LangGraph StateGraph              │
   └───┬──────────┬──────────┬────────────────┘
       │          │          │
  ┌────▼───┐ ┌───▼────┐ ┌──▼──────────┐
  │Customer│ │Billing │ │Network      │   Specialist Agents
  │Support │ │Analyst │ │Diagnostic   │   (LangGraph ReAct)
  │Agent   │ │Agent   │ │Agent        │
  └────────┘ └────────┘ └─────────────┘
       │          │          │
       ▼          ▼          ▼
   ┌──────────────────────────────────────────┐
   │     MCP Servers (Dynamic Tool Discovery)  │
   │     customer / billing / network / campaign│
   └──────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Web Framework | FastAPI, Pydantic v2, Uvicorn |
| AI/Agent | LangGraph, LangChain, DeepSeek API (OpenAI-compatible) |
| Tool Protocol | FastMCP (Model Context Protocol) |
| Database | PostgreSQL + pgvector, SQLAlchemy (async) |
| Messaging | Apache Kafka (aiokafka) |
| Cache/Memory | Redis (agent session memory) |
| Auth | Keycloak (OAuth2.0/OIDC, JWKS, RBAC) |
| Observability | Prometheus, Grafana, Loki, Jaeger, LangSmith |
| Infrastructure | Docker Compose, Helm/K8s, Traefik |

## Project Structure

```
services/
├── customer/          # Customer management (aggregate, CQRS, outbox)
├── billing/           # Invoice & payment processing
├── network/           # Network node monitoring & diagnostics
└── campaign/          # Campaign creation with A/B testing

agents/
├── customer_support/  # Complaint handling (reference implementation)
├── billing_analyst/   # Dispute resolution & anomaly detection
├── network_diagnostic/# Fault diagnosis with multi-persona simulation
├── campaign/          # AI-powered campaign generation
└── orchestrator/      # Supervisor agent — routes to specialists

shared/
├── models/            # DDD base: AggregateRoot, Entity, ValueObject
├── events/            # DomainEvent base class
├── config/            # Centralized settings (pydantic-settings)
├── auth/              # Keycloak JWT validation middleware
├── security/          # Prompt injection guard
├── kafka/             # Retry handler with exponential backoff + DLQ
└── utils/             # Async database session factory

infrastructure/
├── mcp/               # MCP servers + client + OpenAPI-to-MCP generator
├── keycloak/          # Realm config (roles, service clients)
├── monitoring/        # Prometheus rules, Grafana dashboards, Loki
├── docker/            # init-db.sql, Dockerfiles
└── k8s/               # Helm charts for production deployment
```

## Key Design Patterns

**Domain-Driven Design** — Each service is a bounded context with aggregate roots, value objects, domain events, repository interfaces, and CQRS command/query handlers.

**Outbox Pattern** — Domain events are saved to the `outbox.events` table in the same transaction as the aggregate, then polled and published to Kafka. Zero event loss guarantee.

**Supervisor Agent** — The orchestrator classifies incoming events and routes them to the appropriate specialist agent (billing, network, campaign, or customer support).

**MCP Tool Discovery** — Agents can dynamically discover available tools from MCP servers at runtime, or use statically defined LangChain tools.

**Prompt Injection Guard** — All user-controlled text is scanned for injection patterns (role hijacking, system prompt extraction, delimiter injection, tool manipulation) before reaching the LLM. HIGH-risk patterns are blocked; MEDIUM-risk patterns are redacted.

**Retry + DLQ** — Failed Kafka message processing retries with exponential backoff (max 3 attempts), then routes to dead-letter queue.

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (package manager)
- Docker & Docker Compose

### Setup

```bash
# Clone and install
git clone https://github.com/Xreath/TelcoAgentPlatform.git
cd TelcoAgentPlatform
uv sync --extra dev

# Configure environment
cp .env.example .env
# Edit .env with your DeepSeek API key and LangSmith key

# Start infrastructure
docker compose up -d

# Run a service
uvicorn services.customer.api.main:app --reload --port 8001

# Run the agent (Kafka consumer)
python -m agents.customer_support.main

# Run tests
pytest
```

### Service Ports

| Service | Port |
|---------|------|
| Customer Service | 8001 |
| Billing Service | 8002 |
| Network Service | 8003 |
| Campaign Service | 8004 |
| Keycloak | 8080 |
| Kafka UI | 8082 |
| Traefik Dashboard | 8090 |
| Prometheus | 9090 |
| Grafana | 3000 |
| Jaeger UI | 16686 |

## Agent Details

### Customer Support Agent
Handles customer complaints with Turkish-language system prompt. Routes by priority (critical/high/medium/low) and customer segment (gold/platinum first). Tools: profile lookup, billing info, ticket creation, notification.

### Billing Analyst Agent
Detects invoice anomalies (>30% deviation), resolves billing disputes with structured approve/reject/partial decisions. Segment-based retention logic for high-value customers.

### Network Diagnostic Agent
Multi-persona simulation (Analyst → Engineer → Manager). Runs diagnostics (ping, traceroute, bandwidth tests), escalates critical issues (>2% packet loss, >100ms latency, full outage).

### Campaign Agent
Generates segment-targeted campaign content across channels (email, SMS, push, in-app). A/B variant tracking. Channel-specific constraints (SMS ≤160 chars, push ≤50 chars).

## Security

- **OAuth2.0/OIDC** — Keycloak JWT validation with JWKS caching and role-based access control (`agent-operator`, `agent-supervisor`, `agent-auditor`)
- **Prompt Injection Guard** — Regex-based detection with 7 pattern categories across 3 risk levels, supporting both English and Turkish patterns
- **Input Sanitization** — All user-controlled fields are sanitized before LLM processing with 2000-char length limit

## Observability

- **Metrics** — Prometheus counters/histograms for agent invocations, tool calls, errors
- **Logging** — Structured logging via structlog
- **Tracing** — OpenTelemetry + Jaeger for distributed tracing
- **LLM Tracing** — LangSmith integration for agent execution traces
- **Dashboards** — Pre-configured Grafana dashboards with AlertManager rules

## Development

```bash
# Lint & format
ruff check . && ruff format .

# Type check (strict mode)
mypy .

# Benchmark REST vs MCP
python scripts/benchmark_protocols.py

# Seed mock data
python scripts/seed_mock_data.py
```

## License

MIT
