# TelcoAgent Platform
## Enterprise Agentic AI System — XXXX Senior AI Engineer Job Posting Skill Acquisition Project

> **Project Goal:** Learn all the technical requirements from XXXX's AI Engineer job posting through a single, realistic system. Apply DDD, Agentic AI, event-driven microservices, LLM operationalization, Kubernetes, and security architecture at production quality.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Domain-Driven Design (DDD) Architecture](#2-domain-driven-design-ddd-architecture)
3. [Agentic AI System](#3-agentic-ai-system)
4. [Event-Driven Architecture & Kafka](#4-event-driven-architecture--kafka)
5. [LLM Operationalization & MLOps](#5-llm-operationalization--mlops)
6. [API Strategy & Security Architecture](#6-api-strategy--security-architecture)
7. [Kubernetes & Cloud-Native Operations](#7-kubernetes--cloud-native-operations)
8. [Weekly Development Plan (8 Weeks)](#8-weekly-development-plan-8-weeks)
9. [Technology Stack](#9-technology-stack)
10. [Interview Preparation & Career Impact](#10-interview-preparation--career-impact)

---

## 1. Project Overview

**TelcoAgent Platform** is an enterprise-scale system composed of autonomous AI agents, designed for a telecom operator (XXXX scenario). The platform autonomously manages critical business processes such as customer service, network fault detection, billing analysis, and campaign recommendations.

### Why This Project?

- The job posting explicitly emphasizes agentic systems working at enterprise quality — this project targets that standard.
- All requirements including DDD, MCP, event-driven architecture, and LLM operationalization converge into a single cohesive system.
- As a portfolio project, you can discuss every architectural decision during interviews.

### High-Level System Architecture

The platform consists of five main layers:

```
┌─────────────────────────────────────────────────────────────────┐
│              API Gateway & Security Layer                       │
│              Kong + Keycloak + OAuth2.0                         │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│              Orchestration Layer                                │
│         LangGraph Multi-Agent + Temporal Workflow               │
└──────┬──────────────┬──────────────┬──────────────┬────────────┘
       │              │              │              │
┌──────▼──────┐ ┌─────▼──────┐ ┌────▼──────┐ ┌────▼──────┐
│  Customer   │ │  Network   │ │  Billing  │ │ Campaign  │
│  Domain     │ │  Domain    │ │  Domain   │ │  Domain   │
│  Service    │ │  Service   │ │  Service  │ │  Service  │
└──────┬──────┘ └─────┬──────┘ └────┬──────┘ └────┬──────┘
       │              │              │              │
┌──────▼──────────────▼──────────────▼──────────────▼────────────┐
│                  Event Streaming Layer                          │
│                  Apache Kafka + Schema Registry                 │
└─────────────────────────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────────────────┐
│              LLM Inference & MLOps Layer                        │
│         vLLM + MLflow + Prometheus/Grafana + LangSmith          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Domain-Driven Design (DDD) Architecture

The most prominent technical requirement in the posting: the ability to solve complex business problems using DDD principles. This section defines the platform's four Bounded Contexts.

### 2.1 Bounded Contexts

| Bounded Context | Responsibility | Technical Competency |
|---|---|---|
| **Customer Domain** | Customer profile, CLV calculation, personalization | Aggregate Root: `Customer`, Repository pattern, CQRS |
| **Network Domain** | Network topology, fault detection, capacity planning | Publishing to other services via Domain Events |
| **Billing Domain** | Invoice calculation, payment plans, anomaly detection | Distributed transaction management via Saga pattern |
| **Campaign Domain** | Campaign segmentation, AI-based recommendation, A/B testing | LLM integration lives in this context |

### 2.2 Folder Structure (Per Domain Service)

```
customer-service/
├── domain/
│   ├── model/
│   │   ├── customer.py          # Aggregate Root
│   │   ├── value_objects.py     # PhoneNumber, CustomerSegment
│   │   └── events.py            # CustomerCreated, SegmentChanged
│   ├── repository.py            # Abstract repository interface
│   └── services.py              # Domain services (pure business logic)
├── application/
│   ├── commands/                # CQRS write side
│   ├── queries/                 # CQRS read side
│   └── handlers.py
├── infrastructure/
│   ├── postgres_repository.py   # Concrete repository
│   ├── kafka_publisher.py       # Domain event → Kafka
│   └── mcp_server.py            # MCP tool definitions
└── api/
    └── routes.py                # FastAPI endpoints
```

### 2.3 Learning Outcomes

- Aggregate design and invariant protection strategies
- Domain Event design and event storming workshop simulation
- Legacy system integration via Anti-Corruption Layer (ACL)
- Drawing a Context Map and managing inter-service contracts

---

## 3. Agentic AI System

The heart of the posting: *"Designs Agentic AI systems capable of taking autonomous actions toward objectives."*

### 3.1 Agent Hierarchy

```
                    ┌─────────────────────┐
                    │   Supervisor Agent  │
                    │   (LangGraph)       │
                    │   Orchestrator      │
                    └──────┬──────────────┘
                           │ routes tasks
           ┌───────────────┼───────────────┬───────────────┐
           │               │               │               │
┌──────────▼─────┐ ┌───────▼──────┐ ┌─────▼────────┐ ┌───▼──────────────┐
│ CustomerSupport│ │  Network     │ │   Billing    │ │    Campaign      │
│     Agent      │ │  Diagnostic  │ │   Analyst    │ │     Agent        │
│                │ │    Agent     │ │    Agent     │ │                  │
│ LangGraph      │ │   AutoGen    │ │  LangGraph   │ │ LangGraph +      │
│ ReAct + Tools  │ │ Group Chat + │ │ Structured   │ │ Fine-tuned LLM   │
│ Redis Memory   │ │ Code Exec    │ │ Output       │ │ A/B Framework    │
└────────────────┘ └──────────────┘ └──────────────┘ └──────────────────┘
```

#### CustomerSupportAgent
- **Task:** Customer complaint analysis, resolution proposals, escalation decisions
- **Technology:** LangGraph ReAct Agent + Tool Calling + Memory (Redis)
- **Tools:** `get_customer_profile`, `get_billing_history`, `create_ticket`, `send_notification`

#### NetworkDiagnosticAgent
- **Task:** Network anomaly detection, root-cause analysis, automated ticket creation
- **Technology:** AutoGen Group Chat + Python code executor tool
- **Tools:** `query_network_topology`, `run_diagnostic_script`, `escalate_to_ops`

#### BillingAnalystAgent
- **Task:** Invoice anomaly detection, explanation generation, dispute management
- **Technology:** LangGraph + Structured Output + CQRS event sourcing
- **Tools:** `get_invoice_detail`, `detect_anomaly`, `generate_explanation`, `process_dispute`

#### CampaignAgent
- **Task:** Customer segmentation, personalized campaign text generation
- **Technology:** LangGraph + Fine-tuned LLM + A/B test framework
- **Tools:** `get_customer_segment`, `generate_campaign_text`, `log_ab_variant`

### 3.2 LangGraph State Definition

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    customer_id: str
    domain: str                    # "billing" | "network" | "campaign"
    tools_used: list[str]
    memory_context: dict           # History fetched from Redis
    routing_decision: str          # Supervisor's routing decision
    final_response: str | None
```

### 3.3 MCP (Model Context Protocol) Integration

The posting separately emphasizes the ability to *"optimize next-generation standards like Model Context Protocol (MCP)."*

```
Agent Orchestrator
      │
      │  MCP Protocol (SSE / stdio)
      │
 ┌────▼──────────────────────────────────────┐
 │  MCP Servers (separate per domain)        │
 │                                           │
 │  customer-mcp:8001  →  Customer Domain    │
 │  network-mcp:8002   →  Network Domain     │
 │  billing-mcp:8003   →  Billing Domain     │
 │  campaign-mcp:8004  →  Campaign Domain    │
 └───────────────────────────────────────────┘
```

- Each Bounded Context exposes its own MCP server
- MCP tool definitions are automatically generated from OpenAPI schemas
- Agents perform dynamic tool discovery via MCP protocol — no hardcoded tool lists
- Performance comparison between gRPC and MCP is conducted and tested in production

### 3.4 Memory Management Strategy

| Memory Type | Technology | Usage |
|---|---|---|
| **Short-term** | Redis | Agent session state, current conversation context |
| **Long-term** | pgvector (PostgreSQL) | Customer history, solution embeddings |
| **Episodic** | MongoDB | Past agent flows, decision traces |
| **Semantic** | Qdrant | Domain knowledge base, FAQ embeddings, similar case retrieval |

---

## 4. Event-Driven Architecture & Kafka

### 4.1 Core Event Flows

| Event | Producer | Consumer(s) |
|---|---|---|
| `customer.complaint.created` | CustomerAPI | CustomerSupportAgent, BillingAgent |
| `network.anomaly.detected` | NetworkMonitorService | NetworkDiagnosticAgent, OpsTeamNotifier |
| `agent.decision.made` | Every Agent | AuditLog Service, MLOps Monitoring |
| `llm.inference.completed` | LLM Service | BillingAgent (cost tracking), Observability |
| `campaign.generated` | CampaignAgent | CustomerNotificationService, A/B Test Framework |
| `billing.anomaly.found` | BillingAgent | FraudDetectionService, CustomerService |

### 4.2 Kafka Topic Structure

```
telco.customers.*          # Customer domain events
telco.network.*            # Network domain events
telco.billing.*            # Billing domain events
telco.campaigns.*          # Campaign domain events
telco.agents.decisions     # All agent decisions (audit)
telco.llm.metrics          # LLM inference metrics
telco.dlq.*                # Dead Letter Queue (failed messages)
```

### 4.3 Outbox Pattern (Distributed Transaction)

```python
# Single DB transaction inside the service:
async def create_customer_and_publish(customer_data):
    async with db.transaction():
        # 1. Save the main record
        customer = await customer_repo.save(customer_data)
        # 2. Write to outbox table (within the same transaction)
        await outbox_repo.save({
            "aggregate_id": customer.id,
            "event_type": "customer.created",
            "payload": customer.to_dict()
        })
    # A separate process reads the outbox and publishes to Kafka
```

### 4.4 Temporal for Fault-Tolerant Workflows

The posting specifically emphasizes *"designing systems that manage complex, fault-tolerant workflows with tools like Temporal or Airflow."*

```python
# Customer complaint saga workflow
@workflow.defn
class CustomerComplaintWorkflow:

    @workflow.run
    async def run(self, complaint_id: str) -> str:
        # Each step has automatic retries and is durable
        customer = await workflow.execute_activity(
            fetch_customer_data, complaint_id,
            retry_policy=RetryPolicy(max_attempts=3)
        )
        analysis = await workflow.execute_activity(
            run_agent_analysis, customer,
            start_to_close_timeout=timedelta(minutes=5)
        )
        if analysis.needs_approval:
            # Wait for signal — Temporal preserves state while workflow is paused
            await workflow.wait_condition(lambda: self._approved)

        await workflow.execute_activity(send_resolution, analysis)
        return "resolved"
```

### 4.5 Learning Outcomes

- Kafka topic partitioning strategy and consumer group design
- Distributed transaction alternatives with exactly-once semantics (Outbox Pattern)
- Real-time event processing with Kafka Streams (sliding window for anomaly detection)
- Schema evolution without breaking changes using Schema Registry (Avro)
- Temporal: Activity definitions, idempotency guarantees, signals/queries in long-running workflows

---

## 5. LLM Operationalization & MLOps

The most critical "nice to have" section in the posting: *"Architectural experience in operationalizing, versioning, and monitoring LLM behavior in production systems."*

### 5.1 Model Management (MLflow)

```
MLflow Model Registry
├── CustomerSupportLLM
│   ├── v1.0 — Staging (llama-3.1-8b fine-tuned)
│   ├── v1.1 — Production (llama-3.1-8b + RAG)
│   └── v2.0 — Candidate (llama-3.1-70b)
├── CampaignGeneratorLLM
│   ├── v1.0 — Production
│   └── v1.1 — A/B Testing (20% traffic)
└── NetworkDiagnosticLLM
    └── v1.0 — Production
```

### 5.2 A/B Test Framework

```python
class LLMRouter:
    def route(self, agent_type: str, request: dict) -> LLMClient:
        experiment = self.feature_flags.get(f"llm.{agent_type}")

        if experiment.is_active and random() < experiment.traffic_split:
            # B variant — new model
            self.metrics.increment("ab_test.variant_b", tags={"agent": agent_type})
            return self.get_model(experiment.variant_b)

        # A variant — production model
        return self.get_model(experiment.variant_a)
```

### 5.3 Observability Stack

```
LLM Observability Pyramid:

📊 Metrics (Prometheus + Grafana)
   └── token_usage_total, latency_p99, error_rate, cost_per_request

📋 Logs (ELK Stack)
   └── Per LLM call: prompt_hash, response_length, model_version, cost

🔍 Traces (Jaeger + LangSmith)
   └── Agent decision tree, tool call durations, retries, token breakdown

🚨 Alerts (Alertmanager)
   └── Token budget exceeded, latency spike (>5s), output quality drop
```

### 5.4 LLM-as-Judge Quality Evaluation

```python
@evaluation_step
async def evaluate_response_quality(
    original_request: str,
    agent_response: str,
    model: str = "gpt-4o"  # Stronger model for evaluation
) -> QualityScore:
    """Automatically evaluate every production agent response."""
    prompt = JUDGE_PROMPT.format(
        request=original_request,
        response=agent_response,
        criteria=["accuracy", "helpfulness", "safety", "coherence"]
    )
    score = await llm_client.evaluate(prompt, model=model)
    await metrics.gauge("agent.response.quality", score.overall, tags={"model": model})
    return score
```

### 5.5 Prompt Management

- Prompt templates are versioned in Git and integrated into the CI/CD pipeline
- Prompt A/B testing and performance comparison via LangSmith hub
- Guard layer against prompt injection attacks (Llama Guard or custom classifier)

---

## 6. API Strategy & Security Architecture

### 6.1 API Layers

| API Type | Use Case | Technology |
|---|---|---|
| **REST** | External developer API, customer applications | FastAPI + OpenAPI 3.1, versioning (`/v1/`, `/v2/`) |
| **gRPC** | Internal microservice communication | Protobuf schema, bi-directional streaming |
| **WebSocket** | Real-time agent status updates | FastAPI WebSocket, live chat |
| **MCP Protocol** | Agent-to-tool communication | Standardized tool discovery and invocation |

### 6.2 Identity & Access Management (Keycloak)

```
Keycloak Realm: telco-agents
├── Clients
│   ├── customer-service     → Client Credentials flow
│   ├── network-service      → Client Credentials flow
│   ├── billing-service      → Client Credentials flow
│   ├── agent-orchestrator   → Client Credentials flow
│   └── admin-ui             → Authorization Code flow
├── Roles
│   ├── agent-operator       → Can run agents
│   ├── agent-supervisor     → Can override agent decisions
│   └── agent-auditor        → Read-only access
└── Scopes
    ├── customer:read / customer:write
    ├── network:read / network:incident:create
    └── billing:read / billing:dispute:create
```

### 6.3 OAuth2.0 Flow Selection

```python
# Service-to-service: Client Credentials
async def get_service_token(service: str) -> str:
    response = await keycloak.token(
        grant_type="client_credentials",
        client_id=service,
        client_secret=settings.get_secret(service)
    )
    return response["access_token"]

# Middleware: Validate token on every request
@app.middleware("http")
async def validate_token(request: Request, call_next):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    claims = await keycloak.introspect(token)
    if not claims["active"]:
        raise HTTPException(status_code=401)
    request.state.user = claims
    return await call_next(request)
```

### 6.4 API Gateway (Kong) Configuration

```yaml
# Rate limiting — token bucket for LLM endpoint
plugins:
  - name: rate-limiting
    config:
      minute: 60
      hour: 1000
      policy: local
      limit_by: consumer

# Circuit breaker
  - name: response-ratelimiting
    config:
      limits:
        llm_tokens:
          minute: 100000  # token budget
```

---

## 7. Kubernetes & Cloud-Native Operations

### 7.1 Namespace Structure

```
telco-agents (namespace)
├── agent-orchestrator     # LangGraph supervisor + workers
├── customer-service       # FastAPI + gRPC
├── network-service        # FastAPI + gRPC
├── billing-service        # FastAPI + gRPC
├── campaign-service       # FastAPI + gRPC
├── temporal-workers       # Workflow executors
├── kafka-consumers        # Domain event consumers
└── llm-inference          # vLLM serving (GPU nodepool)

infra (namespace)
├── kafka                  # Strimzi Kafka operator
├── keycloak               # Identity provider
├── temporal               # Workflow engine
├── mlflow                 # Model registry
├── prometheus             # Metrics
├── grafana                # Dashboards
└── jaeger                 # Distributed tracing
```

### 7.2 Critical Design Decisions

| Topic | Decision | Rationale |
|---|---|---|
| **LLM Inference Pods** | GPU node pool separation + node affinity | GPU memory management, cost isolation |
| **Kafka Consumers** | KEDA consumer lag HPA | Auto-scale based on lag metric — CPU metric is insufficient |
| **Temporal Workers** | Deployment (stateless) | Workflow state lives in Temporal, workers are stateless |
| **Agent Orchestrator** | Liveness probe initialDelaySeconds: 60 | LLM warmup time must be accounted for |
| **Secrets** | Kubernetes Secrets + Vault | Vault Agent Injector for secret rotation |

### 7.3 KEDA Kafka Consumer Autoscaling

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: customer-agent-scaler
spec:
  scaleTargetRef:
    name: customer-support-agent
  minReplicaCount: 2
  maxReplicaCount: 20
  triggers:
    - type: kafka
      metadata:
        bootstrapServers: kafka:9092
        topic: telco.customers.complaints
        consumerGroup: customer-agent-group
        lagThreshold: "50"     # Spin up 1 more pod when 50 messages pile up
```

### 7.4 Resilience Engineering

```python
# Circuit breaker (tenacity)
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
)
async def call_llm_with_resilience(prompt: str) -> str:
    try:
        return await llm_client.generate(prompt)
    except LLMUnavailableError:
        # Fallback: rule-based response
        return await rule_based_fallback(prompt)
```

---

## 8. Weekly Development Plan (8 Weeks)

### Week 1 — Core Architecture & Infrastructure

**Goal:** A working local development stack

- [ ] Project repo structure (monorepo — each service in its own folder)
- [ ] Full stack via Docker Compose: Kafka, PostgreSQL, Redis, Keycloak, Temporal
- [ ] DDD Bounded Context design — write an Event Storming document
- [ ] First Customer Domain model (Aggregate, Value Objects, Domain Events)
- [ ] Keycloak realm configuration, first clients and roles

**End-of-week deliverable:** Full infrastructure comes up with `docker compose up`

---

### Week 2 — Domain Microservices

**Goal:** 2 domain services running, events flowing into Kafka

- [ ] Customer Service (FastAPI + PostgreSQL)
  - REST endpoints (`/v1/customers`, CRUD)
  - Repository pattern implementation
  - Domain event → Kafka publisher (Outbox Pattern)
- [ ] Billing Service (FastAPI + PostgreSQL)
  - Invoice CRUD, anomaly detection rules
  - CQRS: separate read/write model
- [ ] gRPC service definitions (`.proto` files)
- [ ] pgvector setup, first embedding operation

**End-of-week deliverable:** Creating a customer complaint publishes an event to Kafka

---

### Week 3 — First Agent

**Goal:** CustomerSupportAgent working end-to-end

- [ ] LangGraph ReAct agent setup
- [ ] Tool definitions (4 tools: profile, billing, ticket, notification)
- [ ] Redis memory integration (short-term memory)
- [ ] LangSmith tracing active
- [ ] Kafka consumer: complaint event → agent triggered
- [ ] Basic Prometheus metrics (latency, token usage)

**End-of-week deliverable:** When a customer complaint hits Kafka, the agent analyzes it and creates a ticket

---

### Week 4 — MCP Layer

**Goal:** Agents discover tools dynamically via MCP

- [ ] Customer domain MCP server (FastMCP or custom)
- [ ] Billing domain MCP server
- [ ] Agent MCP client integration — tool list is not hardcoded
- [ ] REST vs gRPC vs MCP performance comparison (benchmark script)
- [ ] Auto-generate MCP tool definitions from OpenAPI

**End-of-week deliverable:** Adding a new tool works without restarting the agent

---

### Week 5 — Multi-Agent Orchestration

**Goal:** Supervisor + 4 agents running together

- [ ] LangGraph Supervisor agent (routing logic)
- [ ] NetworkDiagnosticAgent (AutoGen Group Chat)
- [ ] CampaignAgent (LLM + A/B variant selection)
- [ ] Agent-to-agent communication (via Kafka)
- [ ] LangGraph conditional edges (which agent to route to?)

**End-of-week deliverable:** A complex complaint (involving both billing and network) routes to the correct agents

---

### Week 6 — Workflows & Streaming

**Goal:** Fault-tolerant workflows and real-time anomaly detection

- [ ] Temporal: CustomerComplaintWorkflow (retry, signal, query)
- [ ] Kafka Streams: Network anomaly detection (sliding window — 3+ errors in 5 minutes → alert)
- [ ] KEDA ScaledObject configuration
- [ ] Schema Registry: Avro schemas, schema evolution test
- [ ] Dead Letter Queue strategy and monitoring

**End-of-week deliverable:** Even after a Temporal worker crash, the workflow resumes from where it left off

---

### Week 7 — MLOps & Observability

**Goal:** Production-grade monitoring and model management

- [ ] MLflow model registry setup, first model registration
- [ ] A/B test framework (LLMRouter + feature flag)
- [ ] Prometheus/Grafana dashboard (token usage, latency, cost, quality)
- [ ] LLM-as-judge quality evaluation pipeline
- [ ] Jaeger distributed tracing (integrated across all services)
- [ ] Alertmanager rules

**End-of-week deliverable:** Alert fires in Grafana when an agent exceeds its token budget

---

### Week 8 — Kubernetes & Production Readiness

**Goal:** Full deployment on Kubernetes, chaos tests passing

- [ ] Kubernetes manifests (Deployment, Service, ConfigMap, Secret)
- [ ] Helm chart authoring
- [ ] KEDA configuration migrated to production
- [ ] Chaos Mesh: pod kill and network partition tests
- [ ] API documentation (OpenAPI, Postman collection)
- [ ] Architectural Decision Records (ADR) written up
- [ ] README and system diagrams

**End-of-week deliverable:** Full system running on Minikube/k3d, passing all chaos tests

---

## 9. Technology Stack (Finalized)

> **Note:** Bu tablo planlama aşamasında alınan kararlarla güncellenmiştir. Detaylı kararlar ve gerekçeler için `findings.md` dosyasına bakınız.

| Layer | Primary (Kesinleşmiş) | Notes |
|---|---|---|
| **Primary Language** | Python (FastAPI) | Tüm servisler, polyglot yok |
| **AI Orchestration** | LangGraph + AutoGen | LangGraph: 3 agent + Supervisor, AutoGen: NetworkDiagnostic |
| **LLM Provider** | DeepSeek API (OpenAI-compatible) | Dev sürecinde, düşük maliyet |
| **LLM Serving (MLOps)** | vLLM + MLflow | MLOps demo aşamasında |
| **Workflow Engine** | Temporal | Direkt başlıyoruz, Celery/Airflow yok |
| **Event Streaming** | Apache Kafka + Schema Registry (Avro) | Enterprise-standard, compact |
| **Main Database** | PostgreSQL | Tüm domain verileri |
| **Vector DB (Embedded)** | pgvector (PostgreSQL ext.) | Long-term memory, embeddings |
| **Vector DB (Semantic)** | Qdrant | FAQ embeddings, similar case retrieval |
| **Cache / Memory** | Redis | Agent short-term memory, session state |
| **Document DB** | MongoDB | Episodic memory, agent decision traces |
| **API Gateway** | Traefik (Week 1-6) → Kong (Week 7-8) | Basit başla, production-grade'e geç |
| **Auth** | Keycloak + OAuth2.0 | Direkt başlıyoruz, basit JWT yok |
| **Metrics** | Prometheus + Grafana | Token usage, latency, cost |
| **Logs** | Loki + Grafana | ELK yerine, daha hafif |
| **Traces** | Jaeger + LangSmith | Distributed + agent-level tracing |
| **Alerts** | Alertmanager | Budget aşımı, latency spike |
| **MCP** | FastMCP | Her domain kendi MCP server'ı |
| **Container (Dev)** | Docker Compose | Week 1-6 local dev |
| **Container (Prod)** | k3d + Helm | Hafif, hızlı local K8s |
| **Autoscaling** | KEDA | Kafka consumer lag-based |
| **Service Mesh** | Istio | Sadece K8s aşamasında |
| **Chaos Testing** | Chaos Mesh | Sadece K8s aşamasında |
| **Protocols** | REST + gRPC + MCP | Her birinin ayrı use case'i var |

### Key Changes from Original Plan
| Original | Changed To | Reason |
|---|---|---|
| ELK Stack (logs) | Loki + Grafana | Daha hafif, Grafana zaten var |
| minikube | k3d | Daha hafif, hızlı, multi-node |
| Custom MCP | FastMCP | Hızlı başlangıç |
| OpenAI API | DeepSeek API | Düşük maliyet, OpenAI-compatible |
| Kong (baştan) | Traefik → Kong | Doğru zamanda doğru tool |
| Polyglot (Go/Java) | Sadece Python | Gereksiz karmaşıklık |
| Celery → Temporal | Direkt Temporal | Sökmek kurmaktan zor |
| Basit JWT → Keycloak | Direkt Keycloak | Erken enterprise auth |

---

## 10. Interview Preparation & Career Impact

### 10.1 Prepare a "Why" for Every Architectural Decision

These are the questions you'll face in interviews. You'll learn the answers by building the project:

| Question | Answer to Prepare |
|---|---|
| "Why Temporal instead of just Kafka?" | Durable execution guarantees; workflow state lives in the platform, not application code |
| "Why DDD?" | Billing, network, and customer are separate bounded contexts in telecom — they change at different rates and belong to different teams |
| "How did you control LLM costs?" | Token budget per agent, semantic caching, small model routing, model selection via A/B testing |
| "Why did you choose MCP?" | Tool standardization, isolating agents from specific tool implementations, dynamic discovery |
| "Which side of the CAP theorem did you favor?" | CP for billing (consistency critical), AP for campaign (availability first) — different contexts, different trade-offs |
| "Why is the Outbox Pattern necessary?" | The only reliable way to atomically guarantee a Kafka publish and a DB write happen together |

### 10.2 Job Posting Requirements ↔ Project Mapping

| Job Posting Requirement | Where in the Project |
|---|---|
| Designing Agentic AI systems | Section 3 — LangGraph + AutoGen multi-agent |
| Domain-Driven Design (DDD) | Section 2 — 4 Bounded Contexts, Aggregates, Domain Events |
| Event-driven architecture + Kafka | Section 4 — Kafka Streams, Schema Registry, Outbox |
| Model Context Protocol (MCP) | Section 3.2 — Every domain exposes an MCP server |
| LLM operationalization | Section 5 — MLflow, A/B testing, observability, LLM-as-judge |
| Temporal fault-tolerant workflow | Section 4.3 — Customer complaint saga workflow |
| Kubernetes in production | Section 7 — HPA, KEDA, Chaos Mesh, Helm |
| Keycloak + OAuth2.0 | Section 6.2 — Full Keycloak realm design |
| gRPC + REST API strategy | Section 6.1 — Use case for each protocol |
| Distributed systems / CAP | Sections 2 + 4 — Different consistency choices for different domains |

### 10.3 ADR (Architectural Decision Records) Template

Write an ADR for every significant decision. This reinforces learning and gives you concrete material for interviews:

```markdown
# ADR-001: Kafka Selected for Inter-Service Communication

## Status
Accepted — 2024-XX-XX

## Context
4 microservices need to react to each other's events.
Synchronous REST calls create temporal coupling.

## Decision
All domain events will be published via Kafka.
Synchronous communication is reserved only for gRPC calls
that require immediate query results.

## Consequences
✅ Services can scale independently
✅ Consumers are unaffected if the producer service goes down
❌ Eventual consistency — no immediate data consistency
❌ Harder to debug — distributed tracing is mandatory
```

---

> 🚀 **When this platform is complete in 8 weeks, you'll be able to defend every architectural decision with real hands-on experience in the XXXX interview.**
