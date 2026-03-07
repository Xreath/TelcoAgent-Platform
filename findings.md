# Findings & Decisions — TelcoAgent Platform

## Project Nature
- **Egitim/kendini gelistirme projesi** — production degil
- Bolca mock data ve kurgu datalar ile calisacagiz
- Gercek telekom verisi yok, realistic fake data uretilecek (Faker, custom generators)
- Amac: Mimari pattern'leri ve teknolojileri ogrenip portfolio'ya eklemek

## Requirements
- 4 Bounded Context: Customer, Network, Billing, Campaign
- 5 katmanli mimari: API Gateway -> Orchestration -> Domain Services -> Event Streaming -> LLM/MLOps
- Supervisor + 4 uzman agent (CustomerSupport, NetworkDiagnostic, BillingAnalyst, Campaign)
- MCP ile dynamic tool discovery (her domain kendi MCP server'i)
- Event-driven: Kafka + Schema Registry + Outbox Pattern
- Temporal fault-tolerant workflows
- MLOps: MLflow + A/B testing + LLM-as-Judge + observability
- Auth: Keycloak + OAuth2.0
- K8s: KEDA + Istio + Chaos Mesh + Helm

## Final Technology Stack (Kesinlesmis)

### Language & Framework
- **Python + FastAPI** — Tum servisler, polyglot yok

### Databases
- **PostgreSQL** — Ana veri (customers, billing, network)
- **pgvector** — PostgreSQL extension, embedding storage (long-term memory)
- **Redis** — Agent short-term memory, cache, session state
- **MongoDB** — Episodic memory (agent decision traces)
- **Qdrant** — Semantic search, FAQ embeddings, similar case retrieval

### Event Streaming
- **Apache Kafka** — Event streaming
- **Schema Registry (Avro)** — Enterprise-standard, compact, schema evolution
- **Kafka UI** — Debug icin gorsel arayuz

### AI/Agent
- **LangGraph** — CustomerSupport, Billing, Campaign agentlari + Supervisor
- **AutoGen** — NetworkDiagnostic agent (Group Chat + Code Executor)
- **DeepSeek API** (OpenAI-compatible) — LLM provider (dev sureci)
- **vLLM** — Local LLM serving (MLOps demo asamasinda)
- **LangSmith** — Agent trace, prompt debug

### Workflow
- **Temporal** — Saga workflows, fault-tolerant, direkt basliyoruz (Celery yok)

### Auth & API Gateway
- **Keycloak** — OAuth2.0, realm/client/role (direkt basliyoruz)
- **Traefik** (Week 1-6) -> **Kong** (Week 7-8)

### Observability
- **Prometheus + Grafana** — Metrics (token usage, latency, cost)
- **Loki + Grafana** — Logs (ELK yerine, daha hafif)
- **Jaeger** — Distributed tracing
- **LangSmith** — Agent-level tracing
- **Alertmanager** — Budget asimi, latency spike alerts

### MCP
- **FastMCP** — Her domain icin MCP server, hizli baslangic

### Container & Orchestration
- **Docker Compose** — Week 1-6 (local dev)
- **k3d** — Local Kubernetes (hafif, hizli)
- **Helm** — K8s manifest yonetimi
- **KEDA** — Kafka consumer autoscaling
- **Istio** — Service mesh (K8s asamasinda)
- **Chaos Mesh** — Resilience testing (K8s asamasinda)

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Grouped monorepo (B yapisi) | services/, agents/, infrastructure/, shared/ — separation of concerns |
| Tum servisler Python/FastAPI | AI/ML ekosistemi native, polyglot gereksiz karmasiklik |
| PostgreSQL + pgvector + MongoDB + Qdrant + Redis | Her birinin ayri amaci var, interview'da zengin hikaye |
| Avro (JSON Schema degil) | Enterprise standard, compact, schema evolution |
| DeepSeek API (OpenAI-compatible) | Dusuk maliyet, OpenAI client ile direkt calisir |
| Temporal direkt (Celery yok) | Sokmek kurmaktan zor, amac Temporal ogrenmek |
| Keycloak direkt (basit JWT degil) | Gercekci enterprise auth, erken entegrasyon |
| Loki (ELK degil) | Grafana zaten var, tek dashboard, cok daha hafif |
| k3d (minikube degil) | Daha hafif, hizli, multi-node destegi |
| FastMCP (custom degil) | Hizli baslangic, protokolu ogrenmek icin yeterli |
| Traefik -> Kong | Basit baslayip production-grade'e gecis hikayesi |
| Istio + Chaos Mesh sadece K8s asamasinda | Dogru zamanda dogru tool |
| Outbox Pattern | Kafka + DB atomic garantisi icin tek guvenilir yol |
| CQRS Billing Service'te | Read/Write ayirimi, event sourcing uyumu |

## DDD Bounded Contexts

### Customer Domain
- Aggregate Root: `Customer`
- Value Objects: PhoneNumber, CustomerSegment, Address
- Events: CustomerCreated, SegmentChanged, ComplaintFiled
- Repository Pattern + CQRS

### Network Domain
- Domain Events publish -> diger servisler consume
- Anomaly detection (Kafka Streams sliding window)
- Tools: query_network_topology, run_diagnostic_script, escalate_to_ops

### Billing Domain
- Saga Pattern (distributed transactions)
- CQRS: ayri read/write model
- Anomaly detection, dispute management
- Events: InvoiceCreated, AnomalyFound, DisputeOpened

### Campaign Domain
- LLM integration (campaign text generation)
- A/B testing framework
- Customer segmentation
- Events: CampaignGenerated, VariantSelected

## Memory Strategy
| Type | Tech | Usage |
|------|------|-------|
| Short-term | Redis | Session state, conversation context |
| Long-term | pgvector | Customer history, solution embeddings |
| Episodic | MongoDB | Agent flows, decision traces |
| Semantic | Qdrant | FAQ embeddings, similar case retrieval |

## Kafka Topic Structure
```
telco.customers.*
telco.network.*
telco.billing.*
telco.campaigns.*
telco.agents.decisions
telco.llm.metrics
telco.dlq.*
```

---

## Phase 1-4 Code Review (2026-03-06)

### CRITICAL BUGS — RESOLVED

| # | Issue | File | Resolution |
|---|-------|------|------------|
| C1 | `_domain_events: list = []` — shared mutable class variable | shared/models/base.py | `PrivateAttr(default_factory=list)` ile degistirildi, TYPE_CHECKING guard eklendi |
| C2 | `mcp_server._tool_manager` doesn't exist in FastMCP | infrastructure/mcp/client.py | `_extract_tool_dict()` fonksiyonu yazildi, 4 farkli FastMCP erişim yolu denenir |
| C3 | Async wrapper closure bug — loop'ta late-binding | infrastructure/mcp/client.py | `_make_langchain_tool()` factory fonksiyonu, `captured_fn = fn` ile closure fix |
| C4 | Tool name mismatch: agent `get_customer_profile`, MCP `customer_get_customer_profile` | agent.py + client.py | Server name prefix kaldirildi, tool isimleri olduğu gibi kullanilir |

### HIGH — Billing Service Eksik Katmanlar — RESOLVED

| # | Issue | Missing File | Resolution |
|---|-------|--------------|------------|
| H1 | Abstract repository interface yok | services/billing/domain/repository.py | Olusturuldu: `InvoiceRepository(ABC)` — save, find_by_id, find_by_customer, delete |
| H2 | Domain services yok | services/billing/domain/services.py | Olusturuldu: `BillingAnomalyService` — %30 threshold ile anomaly detection |
| H3 | CQRS command handlers yok | services/billing/application/commands/handlers.py | Olusturuldu: 4 command (Create, MarkPaid, OpenDispute, ResolveDispute) + handler |
| H4 | CQRS query handlers yok | services/billing/application/queries/handlers.py | Olusturuldu: `InvoiceDTO`, `DisputeDTO` + `BillingQueryHandlers` |
| H5 | Postgres repository yok | services/billing/infrastructure/postgres_repository.py | Olusturuldu: `PostgresInvoiceRepository` — to_orm_dict/to_domain mapping |
| H6 | Kafka publisher / Outbox yok | services/billing/infrastructure/kafka_publisher.py | Olusturuldu: `OutboxRepository` + `OutboxPoller`, 6 billing event type topic mapping |
| H7 | Routes ayri dosyada degil | services/billing/api/routes.py | Olusturuldu: 6 endpoint, UUID path params, CQRS handler delegation |
| H8 | `session.commit()` cagrilmiyor | services/billing/api/main.py | Router pattern'e gecildi, repo flush() + FastAPI dependency auto-commit |

### HIGH — Customer Service Bugs — RESOLVED

| # | Issue | File | Resolution |
|---|-------|------|------------|
| H9 | Address JSONB'den reconstruct edilmiyor | customer/infrastructure/postgres_repository.py | `Address(**orm.address) if orm.address else None` eklendi |
| H10 | OutboxRepository.save()'de flush yok | customer/infrastructure/kafka_publisher.py | `await self._session.flush()` eklendi |
| H11 | CustomerDTO'da address field yok | customer/application/queries/handlers.py | `address: dict[str, str] | None = None` eklendi |

### HIGH — Agent & Kafka Issues — RESOLVED

| # | Issue | File | Resolution |
|---|-------|------|------------|
| H12 | Kafka consumer DLQ yok | agents/customer_support/kafka_consumer.py | DLQ producer (`telco.dlq.complaints`) + `_send_to_dlq()` eklendi |
| H13 | JSON deserialization hatasi yakalanmiyor | agents/customer_support/kafka_consumer.py | `_safe_deserialize()` fonksiyonu ile safe JSON parsing |
| H14 | Event schema validation yok | agents/customer_support/kafka_consumer.py | `ComplaintEvent` Pydantic schema ile validation eklendi |
| H15 | OpenAPI URL construction broken | infrastructure/mcp/openapi_to_mcp.py | `replace("BASE_URL", "BASE_URL")` no-op duzeltildi, unused var kaldirildi |

### MEDIUM — Code Quality & Config — RESOLVED

| # | Issue | File | Resolution |
|---|-------|------|------------|
| M1 | Service URL'leri hard-coded | tools.py, mcp servers | `settings.customer_service_url` / `billing_service_url` kullanilir |
| M2 | Agent timeout yok | agents/customer_support/agent.py | `asyncio.timeout(300)` — 5 dakika timeout eklendi |
| M3 | QueryHandlers'da unused repo | customer/application/queries/handlers.py | Unused `PostgresCustomerRepository` import kaldirildi |
| M4 | UUID parse hatalari 500 donuyor | customer/api/routes.py | Path params `str` → `UUID` — FastAPI otomatik 422 validation |
| M5 | Billing line_items `list[dict]` | billing/domain/model/invoice.py | `list[dict[str, str]] = Field(default_factory=list)` |
| M6 | Billing Dispute modelleme | invoice.py + orm_models.py | Mevcut haliyle birakildi (child entity olarak) |
| M7 | `import uuid` runtime'da | billing/api/main.py | Router pattern'e gecisle cozuldu, tum importlar dosya basinda |
| M8 | Empty __init__.py files | shared/*/__init__.py | `__all__` exports eklendi (models, events, config, utils) |
| M9 | Memory TTL her mesajda reset | agents/customer_support/memory.py | Birakildi — Redis TTL maliyeti ihmal edilebilir |
| M10 | Tool error tracking eksik | agents/customer_support/agent.py | ToolMessage error tracking eklendi |

### Ek Duzeltmeler (Ruff + Mypy)

| # | Issue | Resolution |
|---|-------|------------|
| R1 | `(str, Enum)` → `StrEnum` (UP042) | 5 enum class'i StrEnum'a gecti (customer + billing value_objects) |
| R2 | `FastMCP(description=...)` invalid param | `instructions=` olarak duzeltildi (customer + billing MCP servers) |
| R3 | E402 import ordering | Docstring sonrasi import siralamalari duzeltildi |
| R4 | `Mapped[dict]` generic type params | `Mapped[dict[str, str]]`, `Mapped[list[float] | None]` vb. |
| R5 | Missing return type annotations | `AsyncIterator[None]`, `list[ComplaintDTO]`, `dict[str, Any]` eklendi |
| R6 | mypy duplicate module `campaign` | `explicit_package_bases = true` + `mypy_path = "."` pyproject.toml'a eklendi |
| R7 | Unused F841 variable | openapi_to_mcp.py'de `description` kaldirildi |

### Dogrulama Sonuclari (2026-03-07)

- `ruff check .` — PASSED (0 hata)
- 36/36 Python modulu basariyla import edildi
- MCP server'lar basariyla baslatilabilir

---

## Gap Analysis: task_plan.md vs TelcoAgent_Platform_Project_Plan.md (2026-03-07)

### Section 6 (API Strategy & Security) — Eksik task'lar tespit edildi

| Project Plan (Section 6) | task_plan.md durumu | Aksiyon |
|---------------------------|---------------------|---------|
| Keycloak realm config (6.2) | Phase 1'de done | Tamam, realm JSON mevcut |
| OAuth2.0 Client Credentials flow (6.3) | EKSIK — hicbir fazda yok | Phase 7.5 eklendi |
| Token validation middleware (6.3) | EKSIK — FastAPI'de JWT validation yok | Phase 7.5 eklendi |
| Kong API Gateway (6.4) | Phase 8'de sadece "migration" olarak vardi | Phase 7.5'e tasindi, detaylandirildi |
| Kong rate limiting plugin (6.4) | EKSIK | Phase 7.5 eklendi |
| Kong circuit breaker (6.4) | EKSIK | Phase 7.5 eklendi |
| Kong-Keycloak OIDC (6.2+6.4) | EKSIK | Phase 7.5 eklendi |
| Role-based scopes (6.2) | EKSIK — Keycloak'ta tanimli ama enforce edilmiyor | Phase 7.5 eklendi |
| WebSocket real-time agent status (6.1) | EKSIK | Phase 7.5 eklendi |
| Prompt injection guard (5.5) | EKSIK | Phase 7.5 eklendi |
| telco.llm.metrics Kafka topic (4.2/5.3) | EKSIK | Phase 7 eklendi |
| Long-term memory pgvector agent entegrasyonu (3.4) | pgvector var ama agent'a bagli degil | Phase 5 eklendi |

**Karar:** Yeni "Phase 7.5: API Gateway & Security Layer" eklendi. Kong + OAuth2.0 + endpoint protection bu fazda yapilacak. Phase 8 sadece Kubernetes'e odaklanacak.

---

## Resources
- Proje plani: TelcoAgent_Platform_Project_Plan.md
- LangGraph docs: https://langchain-ai.github.io/langgraph/
- AutoGen docs: https://microsoft.github.io/autogen/
- FastMCP: https://github.com/jlowin/fastmcp
- Temporal Python SDK: https://docs.temporal.io/develop/python

---
*Update this file after every 2 view/browser/search operations*
