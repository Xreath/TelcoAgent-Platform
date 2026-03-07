# Task Plan: TelcoAgent Platform — Enterprise Agentic AI System

## Goal
Telekom operatoru icin enterprise-scale agentic AI platformu gelistirmek. DDD, LangGraph/AutoGen multi-agent, Kafka event-driven, MCP, LLM operationalization, Kubernetes — tum stack'i egitim projesi olarak insa etmek.

## Current Phase
Phase 5

## Phases

### Phase 1: Core Architecture & Infrastructure (Week 1)
- [x] Monorepo folder structure olustur (DDD Bounded Contexts)
- [x] Docker Compose: Kafka, PostgreSQL, Redis, Keycloak, Temporal
- [x] Event Storming dokumani yaz
- [x] Customer Domain model (Aggregate, Value Objects, Domain Events)
- [x] Keycloak realm config, client ve role tanimlari
- [x] Traefik API Gateway (basit config — Kong'a sonra gecirilecek)
- **Status:** complete
- **Deliverable:** `docker compose up` ile tum infra ayaga kalkar ✅

### Phase 2: Domain Microservices (Week 2)
- [x] Customer Service (FastAPI + PostgreSQL + Repository Pattern)
- [x] Billing Service (FastAPI + PostgreSQL + CQRS)
- [x] gRPC .proto tanimlari (inter-service comms)
- [x] Kafka publisher — Outbox Pattern implementasyonu
- [x] pgvector setup, ilk embedding islemleri
- **Status:** complete
- **Deliverable:** Customer complaint olusturulunca Kafka'ya event publish edilir

### Phase 3: First Agent — CustomerSupportAgent (Week 3)
- [x] LangGraph ReAct agent setup
- [x] 4 tool tanimi (profile, billing, ticket, notification)
- [x] Redis memory entegrasyonu (short-term)
- [x] LangSmith tracing aktif
- [x] Kafka consumer: complaint event → agent tetiklenir
- [x] Prometheus metrics (latency, token usage)
- **Status:** complete
- **Deliverable:** Kafka'ya dusen complaint'i agent analiz edip ticket olusturur

### Phase 4: MCP Layer (Week 4)
- [x] Customer domain MCP server
- [x] Billing domain MCP server
- [x] Agent MCP client — dynamic tool discovery
- [x] REST vs gRPC vs MCP benchmark
- [x] OpenAPI → MCP tool auto-generation
- **Status:** complete
- **Deliverable:** Yeni tool ekleme agent restart gerektirmez

### Phase 5: Multi-Agent Orchestration (Week 5)
- [ ] LangGraph Supervisor agent (routing)
- [ ] NetworkDiagnosticAgent (AutoGen Group Chat)
- [ ] BillingAnalystAgent (LangGraph + Structured Output)
- [ ] CampaignAgent (LangGraph + Fine-tuned LLM + A/B)
- [ ] Agent-to-agent comms via Kafka
- [ ] LangGraph conditional edges
- [ ] Long-term memory entegrasyonu (pgvector — solution embeddings, agent'a RAG)
- **Status:** pending
- **Deliverable:** Billing+network iceren complaint dogru agentlara yonlendirilir

### Phase 6: Workflows & Streaming (Week 6)
- [ ] Temporal: CustomerComplaintWorkflow (retry, signal, query)
- [ ] Kafka Streams: Network anomaly detection (sliding window)
- [ ] KEDA ScaledObject config
- [ ] Schema Registry: Avro schemas + evolution test
- [ ] Dead Letter Queue strategy
- **Status:** pending
- **Deliverable:** Temporal worker crash sonrasi workflow kaldigi yerden devam eder

### Phase 7: MLOps & Observability (Week 7)
- [ ] MLflow model registry, ilk model kaydı
- [ ] A/B test framework (LLMRouter + feature flag)
- [ ] Prometheus/Grafana dashboard (token, latency, cost, quality)
- [ ] LLM-as-Judge quality evaluation
- [ ] Jaeger distributed tracing
- [ ] Alertmanager rules
- [ ] telco.llm.metrics Kafka topic (LLM inference metrics — cost, latency, token usage)
- **Status:** pending
- **Deliverable:** Agent token budget asinca Grafana'da alert tetiklenir

### Phase 7.5: API Gateway & Security Layer (Week 7-8)
- [ ] OAuth2.0 token validation middleware (FastAPI dependency)
- [ ] Service-to-service Client Credentials flow (Keycloak token exchange)
- [ ] Role-based endpoint protection (scopes: customer:read, billing:write, etc.)
- [ ] Kong API Gateway kurulumu (docker-compose + declarative config)
- [ ] Kong rate limiting plugin (token bucket — LLM endpoint icin)
- [ ] Kong circuit breaker / response rate limiting (token budget)
- [ ] Kong → Keycloak OIDC entegrasyonu (JWT validation at gateway level)
- [ ] Traefik → Kong migration (routing rules transfer)
- [ ] Prompt injection guard (Llama Guard veya custom classifier)
- [ ] WebSocket endpoint (real-time agent status updates, live chat)
- **Status:** pending
- **Deliverable:** Tum servisler OAuth2.0 ile korunur, Kong uzerinden rate-limited erisim

### Phase 8: Kubernetes & Production Readiness (Week 8)
- [ ] Kubernetes manifests (Deployment, Service, ConfigMap, Secret)
- [ ] Helm chart
- [ ] Istio service mesh
- [ ] KEDA production config
- [ ] Chaos Mesh: pod kill + network partition testleri
- [ ] API docs (OpenAPI + Postman)
- [ ] ADR'ler yazilir
- **Status:** pending
- **Deliverable:** K8s uzerinde full system, chaos testleri gecen

## Key Decisions (Conversation'da Netlestirilen)

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Kapsam: Hepsini yapiyoruz, mock'larla hizlandiriyoruz | Egitim projesi — gercekci ama pragmatik |
| 2 | LLM: Hybrid (API-based dev + vLLM MLOps demo) | Gelistirme hizi + MLOps deneyimi |
| 3 | Agent Framework: LangGraph + AutoGen karmasik | Interview'da iki framework'u de anlatabilme |
| 4 | Infra: Traefik → Kong, Istio/Chaos Mesh sadece K8s asamasinda | Dogru zamanda dogru tool, gereksiz erken karmasiklik yok |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| C1: Shared mutable `_domain_events: list = []` | 1 | `PrivateAttr(default_factory=list)` + TYPE_CHECKING guard |
| C2: FastMCP `_tool_manager` attribute yok | 1 | `_extract_tool_dict()` — 4 farkli erişim yolu deneyen fonksiyon |
| C3: Async closure late-binding loop bug | 1 | `_make_langchain_tool()` factory + `captured_fn = fn` |
| C4: MCP tool name prefix mismatch | 1 | Server name prefix kaldirildi |
| H8: Billing `session.commit()` cagirilmiyor | 1 | CQRS handler pattern'e gecis, repo flush() + auto-commit |
| R2: `FastMCP(description=...)` invalid | 1 | `instructions=` parametresine degistirildi |
| R6: mypy duplicate module name | 1 | `explicit_package_bases = true` pyproject.toml'a eklendi |

## Notes
- Egitim projesi: bazi servisler mock/simplified olacak
- Her hafta sonunda calisan bir deliverable hedefleniyor
- ADR (Architectural Decision Records) her onemli kararda yazilacak
