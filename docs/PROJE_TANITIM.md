# TelcoAgent Platform — Proje Tanıtımı

## Bu Proje Ne?

TelcoAgent Platform, bir telekomünikasyon şirketinin operasyonlarını yöneten **yapay zeka destekli kurumsal bir platformdur**. Müşteri şikayetleri, fatura anlaşmazlıkları, ağ arızaları ve kampanya yönetimi gibi süreçleri **otonom AI agent'lar** aracılığıyla yönetir.

Kısacası: Bir telco şirketinin günlük operasyonlarını, insan müdahalesini minimize ederek, AI agent'larla otomatikleştiren bir sistem.

---

## Ne İşe Yarar?

| Senaryo | Ne Oluyor? |
|---------|-----------|
| Müşteri şikayet ediyor | CustomerSupportAgent şikayeti analiz eder, müşteri profilini çeker, destek bileti oluşturur, bildirim gönderir |
| Fatura itirazı açılıyor | BillingAnalystAgent faturayı geçmiş ortalamayla karşılaştırır, anomali tespit eder, iade/ret/kısmi iade kararı verir (structured output) |
| Ağ arızası tespit ediliyor | NetworkDiagnosticAgent LangGraph ReAct ile 3 perspektiften (Analist, Mühendis, Yönetici) analiz yapar; arızayı teşhis eder, gerekirse eskale eder |
| Kampanya oluşturulacak | CampaignAgent müşteri segmentine göre ton belirler, kanal seçer (SMS/email/push), A/B varyantları üretir |

Tüm bu agent'lar bir **Supervisor (Orkestratör)** tarafından yönetilir. Gelen event'in türüne göre doğru specialist agent'a yönlendirilir.

---

## Mimari Nasıl Çalışıyor?

```
Müşteri/Operatör → REST API (FastAPI) → Domain Service → Outbox → Kafka → Orchestrator → Specialist Agent → Sonuç
```

### Katman Katman:

**1. Domain Servisleri (4 Bounded Context)**
- `Customer Service` (:8001) — Müşteri kaydı, segment yönetimi, şikayet alma
- `Billing Service` (:8002) — Fatura oluşturma, ödeme, itiraz yönetimi
- `Network Service` (:8003) — Ağ düğümü izleme, arıza tespiti
- `Campaign Service` (:8004) — Kampanya oluşturma, A/B test, segment bazlı hedefleme

Her servis kendi içinde **Domain-Driven Design** uyguluyor: Aggregate Root, Value Object, Domain Event, Repository, CQRS (Command/Query Separation).

**2. Event-Driven İletişim (Kafka + Outbox Pattern)**
- Servisler birbirleriyle doğrudan konuşmaz
- Bir domain event (ör. `ComplaintFiled`) önce aynı DB transaction'ında `outbox.events` tablosuna yazılır
- Outbox poller bu event'leri Kafka'ya publish eder
- Bu sayede **veri kaybı sıfır** — DB yazıldıysa event de kesinlikle publish edilir
- Geçici hatalar retry ile çözülür; kalıcı hatalar DLQ'ya gider

**3. AI Agent Katmanı (LangGraph)**

| Agent | Framework | Özellik |
|-------|-----------|---------|
| **Orchestrator** | LangGraph StateGraph | Supervisor — event'i sınıflandırır, doğru specialist'e yönlendirir |
| **CustomerSupportAgent** | LangGraph ReAct | Tool calling: profil çek, bilet oluştur, bildirim gönder |
| **BillingAnalystAgent** | LangGraph + Structured Output | Anomali tespiti, dispute kararı (approve/reject/partial) |
| **NetworkDiagnosticAgent** | LangGraph ReAct | System prompt ile 3 perspektif simülasyonu: Analist + Mühendis + Yönetici |
| **CampaignAgent** | LangGraph ReAct | Segment bazlı kampanya oluşturma, A/B varyant üretimi |

Agent'lar **ReAct** (Reasoning + Acting) döngüsüyle çalışır: düşün → tool çağır → sonucu değerlendir → tekrarla/bitir.

**Long-Term Memory**: pgvector ile geçmiş çözümler embedding olarak saklanır, yeni sorunlarda RAG ile benzer çözümler getirilir.

**4. MCP (Model Context Protocol)**
- 4 domain servisinin de MCP server'ı var: customer, billing, campaign, network
- Agent'lar tool'larını **runtime'da dinamik olarak keşfeder** — yeni tool eklenince agent restart gerektirmez
- MCP server'lar servis erişilemezse **mock data** ile fallback yapar (geliştirme kolaylığı)
- `openapi_to_mcp.py` ile OpenAPI şemasından otomatik MCP tool tanımları üretilebilir

---

## Kullanılan Teknolojiler ve Neden Seçildiler

### Uygulama Katmanı

| Teknoloji | Neden? |
|-----------|--------|
| **FastAPI** | Async, Pydantic entegrasyonu, otomatik OpenAPI docs |
| **Pydantic v2** | Type-safe domain modelleri, settings yönetimi, validation |
| **SQLAlchemy (async)** | Async PostgreSQL erişimi, ORM + migration (Alembic) desteği |
| **asyncpg** | PostgreSQL için yüksek performanslı async driver |
| **structlog** | Structured logging — JSON çıktı, context binding |

### AI / Agent Katmanı

| Teknoloji | Neden? |
|-----------|--------|
| **LangGraph** | Supervisor + specialist multi-agent orchestration. State machine tabanlı, kontrol edilebilir agent akışı |
| **LangGraph** | Tüm agent'lar için ortak framework; NetworkDiagnosticAgent system prompt ile 3 perspektif simülasyonu yapar |
| **LangChain** | Tool tanımlama, LLM abstraction, agent altyapısı |
| **DeepSeek API** | OpenAI-compatible LLM — maliyet avantajı, Türkçe desteği |
| **FastMCP** | Model Context Protocol server/client — dynamic tool discovery standardı |
| **LangSmith** | LLM trace takibi — agent kararları, tool çağrıları, latency izleme |

> **Neden LangGraph?** Bir framework'ü derinlemesine bilmek, ikisini yüzeysel bilmekten değerli. LangGraph'ın state machine yaklaşımı supervisor-specialist pattern'e doğal uyum sağlıyor. Multi-persona simülasyon ise ayrı bir framework gerektirmeden system prompt ile yapılıyor.

### Veri Katmanı

| Teknoloji | Neden? |
|-----------|--------|
| **PostgreSQL + pgvector** | İlişkisel veri + vektör embedding'leri (RAG) tek DB'de |
| **Redis** | Agent session memory — kısa süreli, hızlı erişim |
| **Apache Kafka** | Servisler arası event-driven iletişim, ordering garantisi, replay özelliği |
| **Alembic** | Database migration yönetimi — güvenli schema değişiklikleri |

### Güvenlik

| Teknoloji | Neden? |
|-----------|--------|
| **HS256 JWT (self-contained)** | OAuth2 header flow, RBAC (agent-operator, agent-supervisor, agent-auditor) — harici identity provider gerektirmez |
| **Prompt Injection Guard** | 7 pattern kategorisi, 3 risk seviyesi — LLM'e kötü niyetli girdi gitmesini engeller. Türkçe + İngilizce |

### Altyapı & Gözlemlenebilirlik

| Teknoloji | Neden? |
|-----------|--------|
| **Docker Compose** | Tüm altyapıyı (DB, Redis, Kafka, monitoring) tek komutla ayağa kaldırma |
| **Traefik** | API Gateway — routing, load balancing, service discovery |
| **Prometheus** | Agent metrikleri: latency, tool çağrıları, hata oranları |
| **Alertmanager** | Prometheus alert'larını yönetir, bildirim gönderir |
| **Grafana** | Prometheus metrikleri için dashboard |
| **Loki** | Merkezi log toplama |

---

## Ne Değildir?

- **Gerçek bir production sistemi değildir** — Bir portfolyo/öğrenme projesidir. Gerçek telco verileri kullanmaz, mock data ile çalışır.
- **Tek bir uygulamanın monoliti değildir** — 4 bağımsız bounded context, her biri kendi domain modeli ve API'si ile ayrışmıştır.
- **Sadece bir chatbot değildir** — Agent'lar sadece sohbet etmez; tool çağırır, karar verir, aksiyon alır ve sonuçlarını Kafka'ya yazar.
- **Framework showcase değildir** — Her teknoloji seçimi belirli bir problemi çözmek için yapılmıştır.

---

## Kritik Mimari Kararlar

| Karar | Neden? |
|-------|--------|
| **DDD (Domain-Driven Design)** | Billing, network, customer farklı bounded context — farklı takımlar, farklı değişim hızları. Her birinin kendi domain dili var. |
| **Outbox Pattern** | DB write + Kafka publish atomikliği başka türlü garanti edilemiyor. Dual-write problemi bu pattern ile çözülüyor. |
| **MCP (Model Context Protocol)** | Tool standardizasyonu. Agent'ı tool implementasyonundan izole etmek. Yeni tool eklenince agent kodu değişmiyor. |
| **Supervisor Agent** | Her event'i tek bir agent işleyemez — domain bilgisi gerekiyor. Supervisor sınıflandırır, specialist derinlemesine analiz eder. |
| **pgvector (Qdrant değil)** | Zaten PostgreSQL kullanıyoruz. Ayrı bir vector DB operasyonel yük getirir. pgvector bu ölçekte yeterli. |
| **Kafka (RabbitMQ değil)** | Event ordering, replay özelliği, topic-based routing. Mikroservisler arası event-driven iletişimde Kafka doğal tercih. |
| **CQRS** | Okuma ve yazma modelleri farklı optimize edilebilir. Query handler'lar doğrudan DB'ye gider, command handler'lar aggregate üzerinden çalışır. |
| **Retry + DLQ** | Geçici hatalar (servis timeout, network glitch) retry ile çözülür. Kalıcı hatalar DLQ'ya gider, veri kaybolmaz. |
| **Self-contained JWT (Keycloak değil)** | Harici identity provider operasyonel yük getirir. HS256 symmetric JWT bu ölçekte yeterli; DEV_MODE bypass geliştirmeyi hızlandırır. |
| **NetworkDiagnosticAgent'ta system prompt multi-persona** | Ağ arızası analizi çok bakış açısı gerektirir. Ayrı bir framework (AG2) yerine system prompt ile 3 persona simülasyonu — daha az bağımlılık, aynı etki. |
| **LangSmith tracing** | Agent kararlarını, tool çağrılarını ve latency'yi gözlemlemek için. Prompt debugging ve performans analizi için kritik. |

---

## Veri Akış Örnekleri

### Müşteri Şikayeti → Agent Çözümü

```
1. Müşteri: POST /v1/customers/{id}/complaints
2. Customer Service: ComplaintFiled event → outbox.events tablosu
3. Outbox Poller: Event → Kafka (telco.customers.complaints)
4. Orchestrator Kafka Consumer: Event'i alır
5. Supervisor Agent: "Bu bir müşteri şikayeti" → CustomerSupportAgent'a yönlendir
6. CustomerSupportAgent:
   - get_customer_profile() → Müşteri segmentini öğren
   - get_billing_info() → Fatura geçmişini kontrol et
   - create_ticket() → Destek bileti oluştur
   - send_notification() → Müşteriye bildirim gönder
7. Karar → Kafka (telco.agents.decisions)
```

### Fatura İtirazı → Otomatik Karar

```
1. Operatör: POST /v1/billing/invoices/{id}/dispute
2. DisputeOpened event → Kafka (telco.billing.anomalies)
3. BillingAnalystAgent:
   - detect_anomaly() → Son 6 ay ortalamasından %30+ sapma var mı?
   - get_invoice_detail() → Satır kalemleri ne?
   - Structured Output ile karar: approve_refund | reject | partial_refund
   - process_dispute() → Kararı uygula
4. Gold/Platinum müşteri → retention odaklı karar (iade eğilimi)
```

### Ağ Arızası → Multi-Persona Analiz

```
1. Network Service: NodeDegraded event → Kafka (telco.network.*)
2. NetworkDiagnosticAgent (LangGraph ReAct, 3 perspektifli system prompt):
   - Analist Persona: "Root cause nedir? Hangi metrikler sapıyor?"
   - Mühendis Persona: diagnose_node(), check_neighbors() tool'ları çalıştırır
   - Yönetici Persona: "Eskalasyon gerekli mi? SLA etkisi var mı?"
3. Consensus → Final rapor → Kafka (telco.agents.decisions)
```

---

## Proje Yapısı Özeti

```
services/          → 4 domain servisi (DDD bounded context'ler)
  customer/        → :8001 — Müşteri, şikayet
  billing/         → :8002 — Fatura, ödeme, itiraz
  network/         → :8003 — Ağ düğümü, arıza
  campaign/        → :8004 — Kampanya, A/B test

agents/            → 5 agent (4 specialist + 1 orchestrator)
  customer_support/ → LangGraph ReAct — tam implement
  billing_analyst/  → LangGraph + Structured Output — tam implement
  network_diagnostic/ → LangGraph ReAct, 3-persona system prompt — tam implement
  campaign/         → LangGraph ReAct — tam implement
  orchestrator/     → LangGraph StateGraph Supervisor — tam implement

infrastructure/    → MCP server'lar (4 adet), Docker, monitoring
  mcp/             → customer, billing, campaign, network MCP server'ları
  monitoring/      → Prometheus, Grafana, Alertmanager, Loki config'leri

shared/            → Base class'lar, auth (JWT), security, config, Kafka retry
scripts/           → Mock data seed, benchmark (REST vs MCP)
tests/             → Unit testler (agent, billing, customer, shared)
alembic/           → Database migration'ları
```

---

## Portfolyo Bağlamında Bu Proje

Bu proje, 6 projelik serideki **ilk ve en kapsamlı proje**. Öğrettiği temel konseptler:

- Domain-Driven Design (tam stack: Aggregate, Value Object, Domain Event, Repository, CQRS)
- LangGraph multi-agent orchestration (Supervisor + 4 specialist)
- LangGraph ile multi-agent orchestration (Supervisor + 4 specialist, sistem prompt tabanlı multi-persona)
- Kafka event-driven mimari + Outbox Pattern
- Model Context Protocol (MCP) — dynamic tool discovery
- pgvector ile RAG (long-term memory)
- FastAPI + Pydantic + SQLAlchemy async
- LangSmith ile LLM observability

Serinin diğer projeleri bu temelin üzerine farklı teknolojileri derinlemesine öğretmek için tasarlanmış:
- **TemporalLab**: Fault-tolerant workflow (Saga pattern, durable execution)
- **ResearchAgentLab**: AutoGen + Qdrant + MongoDB + Kafka Streams
- **MLOpsLab**: vLLM serving, MLflow, A/B test, LLM-as-Judge
- **K8sLab**: Kubernetes production patterns (KEDA, Istio, Chaos Mesh)
- **AgentSDKLab**: Claude Agent SDK ile framework'süz agent geliştirme
