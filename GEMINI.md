# GEMINI.md — TelcoAgent Platform Context

## Project Overview
**TelcoAgent Platform** is an enterprise-grade Agentic AI platform designed for Telecom Operations. It follows a microservices architecture, leveraging Domain-Driven Design (DDD) and Event-Driven Architecture (EDA) to handle complex telco workflows like automated customer support, network diagnostics, and personalized campaign management.

### Key Capabilities
- **Multi-Agent Orchestration**: Specialized agents for billing, network, and customer support using LangGraph and AutoGen.
- **Event-Driven Core**: Real-time reaction to domain events via Apache Kafka.
- **Workflow Automation**: Long-running processes managed by Temporal.
- **Semantic Intelligence**: Vector search (pgvector/Qdrant) for RAG-based support and churn prediction.
- **Observability**: Full-stack monitoring with Prometheus, Grafana, and distributed tracing via Jaeger.

---

## Technical Stack
- **Backend**: Python 3.11+, FastAPI (REST API), gRPC (Internal IPC).
- **Data Stores**: 
  - **PostgreSQL**: Primary transactional data + Vector embeddings (pgvector).
  - **Redis**: Caching and session management.
  - **MongoDB**: Episodic memory for agents.
  - **Qdrant**: High-performance vector database.
- **Messaging**: Apache Kafka (KRaft mode) with Avro & Schema Registry.
- **AI/Agents**: LangGraph, LangChain, AutoGen, FastMCP.
- **Workflow**: Temporal.io.
- **Infrastructure**: Docker Compose (Local), Kubernetes (Prod), Traefik (Gateway), Keycloak (Auth).
- **Observability**: OpenTelemetry, Prometheus, Loki, Grafana, Jaeger.

---

## Project Structure
```text
├── agents/             # Multi-agent definitions (Billing, Support, Network, etc.)
├── services/           # Microservices (Customer, Billing, Network, Campaign)
│   └── <service>/
│       ├── api/        # FastAPI entry points and routes
│       ├── application/# Command/Query Handlers (CQRS)
│       ├── domain/     # Aggregate Roots, Entities, Value Objects, Domain Events
│       └── infrastructure/# DB Repositories, Kafka Producers/Consumers
├── shared/             # Common models, utils, and settings used across services
├── infrastructure/     # Configs for Docker, K8s, Kafka, Monitoring, Keycloak
├── scripts/            # Development utilities and data seeders
└── tests/              # Unit, Integration, and E2E tests
```

---

## Development & Operations

### Python Environment (.venv)
- **Virtual Env**: `.venv/` (project-local virtual environment)
- **Python Version**: 3.11

```bash
# Activate environment (always use this before running anything)
source .venv/bin/activate

# Or run commands directly without activating:
.venv/bin/python -m pytest tests/ -v
.venv/bin/ruff check .
```

> **IMPORTANT**: All Python work on this project must use the `.venv` virtual environment.

### Local Setup
1. **Activate Env**: `source .venv/bin/activate`
2. **Dependencies**: `pip install -e ".[dev]"`
3. **Infrastructure**: `docker compose up -d` (starts all DBs, Kafka, Monitoring, Auth).
4. **Environment**: Copy `.env.example` to `.env` and adjust keys (e.g., OpenAI/DeepSeek API Key).
5. **Seed Data**: `python scripts/seed_mock_data.py` (generates sample telco data).

### Running Services
Each service can be run locally using Uvicorn:
```bash
# Example: Start Customer Service
export PYTHONPATH=$PYTHONPATH:.
uvicorn services.customer.api.main:app --reload --port 8001
```

### Quality & Standards
- **Linting/Formatting**: `ruff check .` and `ruff format .` (Line length: 120).
- **Type Checking**: `mypy .` (Strict mode).
- **Testing**: `pytest` (Uses `pytest-asyncio` for async handlers).

---

## Architecture & Design Patterns

### Domain-Driven Design (DDD)
- **Aggregates**: Ensure consistency boundaries (e.g., `Customer` in Customer Service).
- **Domain Events**: Published via Kafka when state changes (e.g., `CustomerSegmentChanged`).
- **Repositories**: Abstracted via interfaces in the Domain layer, implemented in Infrastructure.

### CQRS & Outbox Pattern
- **Write Side**: Command Handlers modify the state.
- **Read Side**: Query Handlers fetch DTOs.
- **Transactional Outbox**: Events are saved to the `outbox` table in the same transaction as the domain change, ensuring "at-least-once" delivery to Kafka.

### Agentic Patterns
- **Orchestrator**: Coordinates tasks between specialized agents.
- **Memory**: Agents use MongoDB for long-term memory and short-term conversation history.
- **RAG**: Network and Support agents query vector stores for technical docs and FAQs.

---

## Key Files for Reference
- `pyproject.toml`: Dependency definitions and tool configurations.
- `docker-compose.yml`: Local infrastructure orchestration.
- `shared/config/settings.py`: Centralized configuration management.
- `docs/adr/`: Architectural Decision Records (e.g., Kafka usage).
- `services/customer/api/main.py`: Template for service initialization.
