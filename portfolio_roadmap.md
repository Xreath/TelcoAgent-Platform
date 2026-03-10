# AI Engineer Portfolio Roadmap

Bu dosya, TelcoAgent Platform üzerindeki konuşmadan çıkan kararları ve ilerleyen projelerin planını belgeliyor.
Her proje tek bir teknoloji/konsepti derinlemesine öğretmek için tasarlandı.

---

## Neden Çok Proje?

Tek projede her şeyi kullanmaya çalışmak:
- Her şeyin yüzeysel kalmasına yol açıyor
- "Neden X seçtiniz?" sorusuna gerçek cevap veremiyorsun
- Bir şey kırılınca neyi debug edeceğini bilemiyorsun
- Proje büyüdükçe çalıştırmak bile zorlaşıyor

**Doğru yaklaşım:** Her projeye bir odak, her odağa gerçek derinlik.

---

## Proje 1: TelcoAgent Platform (Tamamlandı)

**Durum:** TelcoAgent projesi bitti.
**Repo:** `TelcoAgentPlatform`
**Odak:** DDD + Agentic AI + Kafka + MCP

### Ne öğretir?
- Domain-Driven Design (Aggregate, Value Object, Domain Event, Repository, CQRS)
- LangGraph multi-agent orchestration (Supervisor + 4 specialist agent)
- Kafka event-driven mimari + Outbox Pattern
- Model Context Protocol (MCP) — dynamic tool discovery
- pgvector ile RAG (long-term memory)
- FastAPI, Pydantic, SQLAlchemy async

### Tamamlanan
- 4 Bounded Context (Customer, Billing, Network, Campaign) — full DDD stack
- CustomerSupport Agent (tools, Redis memory, Prometheus metrics, Kafka consumer)
- Multi-agent orchestration (Supervisor → routing → 4 agent)
- 4 MCP server (Customer, Billing, Network, Campaign)
- Shared base classes (AggregateRoot, DomainEvent, ValueObject)
- DLQ stratejisi
- Prometheus/Grafana bağlantısı
- Simple JWT auth middleware (HS256)
- Basit Helm chart
- ADR'ler + API docs

### Mülakatta Anlatılacak Kararlar
| Soru | Cevap |
|------|-------|
| Neden DDD? | Billing, network, customer farklı bounded context — farklı takımlar, farklı değişim hızı |
| Neden Outbox Pattern? | DB write + Kafka publish atomikliği başka türlü garanti edilemez |
| Neden MCP? | Tool standardizasyonu, agent'ı tool implementasyonundan izole etmek, dynamic discovery |
| Neden tek LangGraph (AutoGen yok)? | Bir framework'ü derinlemesine bilmek > ikisini yüzeysel bilmek |
| CAP theorem? | Billing → CP (consistency kritik), Campaign → AP (availability önce) |

---

## Proje 2: TemporalLab

**Repo:** `TemporalLab` (oluşturulacak)
**Odak:** Fault-tolerant, durable workflow execution

### Senaryo: E-Ticaret Sipariş Yönetimi

Kullanıcı sipariş verir → çok adımlı süreç başlar: ödeme al → stok düş → kargo oluştur → bildirim gönder.
Her adım hata durumunda otomatik geri alınabilir (compensation / Saga pattern).
Worker crash olsa bile workflow Temporal server'da durur, yeni worker kaldığı yerden devam eder.

### Mimari

```
┌──────────────────────────────────────────────────────┐
│  FastAPI — Sipariş REST API                          │
│  POST /orders → Temporal workflow başlatır            │
│  GET  /orders/{id}/status → Temporal query            │
│  POST /orders/{id}/approve → Temporal signal          │
└──────────────┬───────────────────────────────────────┘
               │ Temporal Client
┌──────────────▼───────────────────────────────────────┐
│  Temporal Server (Docker)                            │
│  Workflow state durable — worker crash'e dayanıklı   │
└──────────────┬───────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────┐
│  Temporal Workers (Python — temporalio SDK)           │
│                                                      │
│  Workflow'lar:                                        │
│  ├── OrderWorkflow        (ana sipariş akışı)        │
│  ├── PaymentSagaWorkflow  (ödeme + rollback)         │
│  └── ShippingWorkflow     (kargo + takip)            │
│                                                      │
│  Activity'ler:                                       │
│  ├── charge_payment()     → mock ödeme servisi       │
│  ├── reserve_stock()      → PostgreSQL stok azalt    │
│  ├── create_shipment()    → mock kargo API           │
│  ├── send_notification()  → mock e-mail/SMS          │
│  ├── refund_payment()     → compensation (rollback)  │
│  └── restore_stock()      → compensation (rollback)  │
└──────────────┬───────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────┐
│  PostgreSQL — Sipariş + Stok verisi                  │
└──────────────────────────────────────────────────────┘
```

### Ne öğretir?

| Kavram | Bu Projede Nasıl Öğrenilir |
|---|---|
| **Workflow** | OrderWorkflow: sipariş baştan sona bir workflow, her adım bir activity |
| **Activity** | charge_payment(), reserve_stock() vb. — her biri idempotent, retry'a dayanıklı |
| **Worker** | Stateless Python process — crash olsa bile workflow Temporal'da durur, yeni worker devam eder |
| **Retry Policy** | Activity başarısız → otomatik retry (max 3, exponential backoff) |
| **Saga / Compensation** | Kargo oluşturulamazsa → stok geri yükle → ödeme iade et (ters sıra) |
| **Signal** | Yüksek tutarlı siparişler onay bekler → `POST /orders/{id}/approve` ile signal gönder |
| **Query** | `GET /orders/{id}/status` → workflow'un o anki durumunu sorgula (dışarıdan) |
| **Timeout** | Activity 30s içinde yanıt vermezse → timeout → compensation tetiklenir |
| **Workflow Versioning** | v1 workflow çalışırken v2 deploy et — eski instance'lar v1 ile biter, yeniler v2 ile başlar |

### Mülakatta Anlatılacak Kararlar
| Soru | Cevap |
|------|-------|
| Neden Temporal (Celery/Airflow değil)? | Celery sadece task queue — durable state yok. Airflow DAG-based, batch için. Temporal gerçek workflow state yönetimi. |
| Saga pattern neden? | Distributed transaction (2PC) microservice'lerde pratik değil. Saga her adımın compensation'ını tanımlar. |
| Worker crash olunca ne olur? | Hiçbir şey kaybolmaz — workflow state Temporal server'da. Yeni worker aynı yerden devam eder. |
| Signal vs polling? | Polling resource waste + gecikme. Signal event-driven, anında tetiklenir, Temporal state'i korur. |

### Neden ayrı proje?
TelcoAgent'a eklenince "Temporal worker crash'inden sonra workflow devam eder" deliverable'ı
gerçekten test edilemiyor. Ayrı, izole bir projede bu senaryoyu tam yaşayabilirsin.

---

## Proje 3: MLOpsLab

**Repo:** `MLOpsLab` (oluşturulacak)
**Odak:** LLM operationalization — model serve, versiyon, A/B test, kalite ölçümü

### Senaryo: LLM Model Yönetim Platformu

Bir soru-cevap servisi: kullanıcı soru sorar → LLM cevap verir. Arka planda iki model versiyonu
(örn. llama-3.1-8b vs 70b) A/B test ile karşılaştırılır. Kalite, maliyet ve latency
trade-off'ları Grafana'da canlı izlenir. Yeni model daha iyiyse otomatik production'a alınır.

### Mimari

```
┌──────────────────────────────────────────────────────┐
│  FastAPI — QA REST API                               │
│  POST /ask → LLMRouter → model A veya B              │
│  GET  /experiments → aktif A/B test durumu            │
└──────────────┬───────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────┐
│  LLMRouter (A/B Traffic Splitter)                    │
│  Feature flag → %80 model A, %20 model B             │
│  Her istek için: model, latency, token, cost kaydet  │
└──────┬───────────────────────┬───────────────────────┘
       │                       │
┌──────▼──────┐         ┌──────▼──────┐
│  vLLM       │         │  vLLM       │
│  Model A    │         │  Model B    │
│  (8b)       │         │  (70b)      │
└──────┬──────┘         └──────┬──────┘
       │                       │
┌──────▼───────────────────────▼───────────────────────┐
│  MLflow Model Registry                               │
│  ├── v1.0 — Production (Model A)                     │
│  ├── v1.1 — Candidate (Model B, A/B testing)         │
│  └── Experiment tracking: metrics, params, artifacts  │
└──────────────┬───────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────┐
│  LLM-as-Judge (kalite değerlendirme)                 │
│  Her response'u daha güçlü model ile skorla          │
│  accuracy, helpfulness, safety, coherence             │
└──────────────┬───────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────┐
│  Prometheus + Grafana                                │
│  token_usage, latency_p99, cost_per_request,         │
│  quality_score, ab_test_variant_distribution          │
└──────────────────────────────────────────────────────┘
```

### Ne öğretir?

| Teknoloji | Bu Projede Ne İçin Kullanılıyor |
|---|---|
| **vLLM** | Kendi modelini GPU'da serve etmek — batching, quantization (GPTQ/AWQ), continuous batching |
| **MLflow** | Model registry: versiyon yönetimi, staging → production geçişi, experiment tracking |
| **A/B test framework** | LLMRouter: traffic splitting, feature flag ile hangi modele yönlendir |
| **LLM-as-Judge** | Her response'u otomatik skorla — kalite düşerse alert, model karşılaştırması |
| **Prompt management** | Prompt template'leri versiyonla, injection guard (basit classifier) |
| **Cost tracking** | Token başına maliyet hesapla, agent/model bazında bütçe takibi |
| **Prometheus + Grafana** | Token usage, latency, cost, quality score dashboard'ları |

### Mülakatta Anlatılacak Kararlar
| Soru | Cevap |
|------|-------|
| Neden vLLM (API değil)? | Kendi modelini serve etmek: maliyet kontrolü, data privacy, custom fine-tune deploy edebilme |
| A/B test nasıl çalışıyor? | Feature flag ile traffic split → her variant'ın metriklerini topla → statistical significance'a ulaşınca karar ver |
| LLM-as-Judge güvenilir mi? | Tek başına değil, ama trend takibi için çok değerli. Human eval ile kalibre edilmeli. |
| Model versioning neden önemli? | Rollback yapabilmek. Yeni model kötüyse 1 dakikada eskisine dön. |

### Neden ayrı proje?
TelcoAgent şu an DeepSeek API kullanıyor — vLLM serving bu context'te anlamsız.
MLOps gerçekten kendi modelini serve ettiğinde öğrenilir.

---

## Proje 4: K8sLab

**Repo:** `K8sLab` (oluşturulacak)
**Odak:** Kubernetes production patterns — deploy, scale, secure, break & recover

### Senaryo: Microservice'leri Production'a Taşı

TelcoAgent'ın core servislerini (Customer Service + CustomerSupport Agent + Kafka) k3d cluster'ına
deploy et. Trafik arttığında otomatik scale olsun, bir pod ölünce sistem kendini toparlasın,
API gateway üzerinden güvenli erişim sağlansın.

### Mimari

```
┌──────────────────────────────────────────────────────┐
│  Kong API Gateway                                    │
│  Rate limiting, JWT validation (Keycloak OIDC),      │
│  circuit breaker                                     │
└──────────────┬───────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────┐
│  Istio Service Mesh                                  │
│  mTLS between services, traffic management,          │
│  canary deployment (%90 v1, %10 v2)                  │
└──────┬───────────────────────┬───────────────────────┘
       │                       │
┌──────▼──────┐         ┌──────▼──────┐
│  customer-  │         │  customer-  │
│  service    │         │  support-   │
│  (Helm)     │         │  agent      │
│  replicas:  │         │  (Helm)     │
│  2-10 (HPA) │         │  KEDA auto  │
└──────┬──────┘         └──────┬──────┘
       │                       │
┌──────▼───────────────────────▼───────────────────────┐
│  Kafka (Strimzi Operator)                            │
│  KEDA: consumer lag > 50 → agent pod +1              │
└──────────────────────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────┐
│  Chaos Mesh                                          │
│  Pod kill, network partition, CPU stress              │
│  → Sistem kendini toparlıyor mu?                     │
└──────────────────────────────────────────────────────┘
```

### Ne öğretir?

| Teknoloji | Bu Projede Ne İçin Kullanılıyor |
|---|---|
| **k3d** | Hafif, multi-node local Kubernetes cluster — laptop'ta production simülasyonu |
| **Helm** | Chart authoring: template, values, dependency. Her servis kendi chart'ı |
| **KEDA** | Kafka consumer lag-based autoscaling — CPU metric yetmez, business metric lazım |
| **HPA** | CPU/memory-based autoscaling — KEDA ile farkını görmek için |
| **Istio** | Service mesh: mTLS (servisler arası şifreli iletişim), canary deployment, traffic shifting |
| **Kong** | API Gateway: rate limiting (token bucket), Keycloak OIDC entegrasyonu, circuit breaker |
| **Chaos Mesh** | Pod kill → servis recovery süresi. Network partition → split-brain davranışı. CPU stress → throttling |
| **Strimzi** | Kafka'yı Kubernetes-native operatör ile yönet — topic, partition, replication hep K8s CRD |

### Mülakatta Anlatılacak Kararlar
| Soru | Cevap |
|------|-------|
| HPA vs KEDA? | HPA CPU/memory bazlı — genel amaçlı. KEDA Kafka lag bazlı — iş yükü anlamlı metrik. Agent'lar için KEDA doğru. |
| Neden Istio? | mTLS: servisler arası zero-trust. Canary: yeni versiyon %10 trafikle test, sorun yoksa %100'e çık. |
| Kong neden gateway? | Plugin ekosistemi zengin. Rate limiting + OIDC + circuit breaker tek yerde. Traefik daha basit ama enterprise yetmez. |
| Chaos testing neden? | "Çalışıyor" demek yetmez. Pod ölünce, ağ kopunca, CPU %100 olunca da çalışması lazım. Chaos test bunu kanıtlar. |

### Neden ayrı proje?
K8s + Istio + Kong + Chaos Mesh hepsini aynı anda öğrenmek mümkün değil.
Izole bir lab ortamında her bileşeni ayrı ayrı ekleyerek öğrenmek çok daha etkili.

---

## Proje 5: ResearchAgentLab

**Repo:** `ResearchAgentLab` (oluşturulacak)
**Odak:** AutoGen + Qdrant + MongoDB + Kafka Streams + Schema Registry + WebSocket

> TelcoAgent'tan çıkarılan teknolojilerin doğal bir senaryo içinde öğrenildiği proje.

### Senaryo: AI Research Assistant

Kullanıcı bir araştırma sorusu sorar → birden fazla agent işbirliği yaparak dokümanları analiz eder,
web'den bilgi toplar, kod çalıştırır → sonuçları real-time olarak kullanıcıya aktarır.

### Mimari

```
┌─────────────────────────────────────────────┐
│  Frontend (WebSocket)                       │
│  Real-time agent durum ve sonuç akışı       │
└──────────────┬──────────────────────────────┘
               │ WebSocket
┌──────────────▼──────────────────────────────┐
│  AutoGen Orchestrator                       │
│  Group Chat: Planner + Researcher + Coder   │
└──────┬──────────────┬───────────────────────┘
       │              │
┌──────▼──────┐ ┌─────▼──────────────────┐
│  Qdrant     │ │  Kafka + Faust         │
│  Knowledge  │ │  Stream Processing     │
│  Base       │ │  + Schema Registry     │
└─────────────┘ └────────────────────────┘
       │
┌──────▼──────────────────────────────────────┐
│  MongoDB                                    │
│  Research sessions, agent traces, results   │
└─────────────────────────────────────────────┘
```

### Ne öğretir?

| Teknoloji | Bu Projede Ne İçin Kullanılıyor |
|---|---|
| **AutoGen** | Multi-agent group chat — Planner, Researcher, Coder agent'ları tartışarak sonuca ulaşır |
| **Qdrant** | Araştırma dokümanlarının embedding'leri, semantic search ile benzer kaynakları bulma |
| **MongoDB** | Araştırma session'ları, agent karar geçmişi, sonuç dokümanları (şemasız, nested) |
| **Kafka + Faust** | Real-time doküman ingestion — yeni kaynak eklenince otomatik embedding + indexleme |
| **Schema Registry (Avro)** | Kafka mesaj şema yönetimi — Faust stream'leri typed, schema evolution test edilir |
| **WebSocket** | Kullanıcıya agent'ların düşünme sürecini real-time aktarma (streaming) |

### Neden bu teknolojiler burada doğal?

- **AutoGen vs LangGraph:** TelcoAgent'ta LangGraph öğrendin. Burada AutoGen'in group chat paradigmasını öğrenirsin — iki framework'ün farkını gerçekten yaşarsın.
- **Qdrant vs pgvector:** TelcoAgent'ta pgvector öğrendin. Burada dedicated vector DB'nin farkını görürsün — collection management, filtering, payload indexing.
- **MongoDB vs PostgreSQL:** Araştırma sonuçları şemasız, iç içe, değişken yapıda — tam MongoDB use case'i.
- **Kafka Streams + Schema Registry:** Yeni doküman eklendikçe real-time embedding pipeline. Schema Registry sayesinde mesaj formatı değiştiğinde consumer'lar kırılmaz.
- **WebSocket:** Agent'lar düşünürken kullanıcı beklemek zorunda kalmamalı — canlı akış.

### Mülakatta Anlatılacak Kararlar
| Soru | Cevap |
|------|-------|
| Neden AutoGen (LangGraph değil)? | Group chat paradigması bu senaryoya daha uygun — agent'lar tartışarak sonuca ulaşıyor |
| pgvector varken neden Qdrant? | Dedicated vector DB: collection management, advanced filtering, horizontal scaling |
| PostgreSQL varken neden MongoDB? | Araştırma çıktıları şemasız ve nested — doküman modeli doğal uyum sağlıyor |
| Schema Registry neden? | Producer/consumer arasında şema kontratı — breaking change'siz evrim |

---

## Proje 6: AgentSDKLab (Opsiyonel)

**Repo:** `AgentSDKLab` (oluşturulacak)
**Odak:** Claude Agent SDK / Anthropic API ile agent geliştirme

### Senaryo: Otonom DevOps Assistant

Kullanıcı doğal dilde görev verir ("staging'e deploy et", "bu bug'ı fixle") →
Claude agent görevi analiz eder → gerekli tool'ları çağırır (GitHub API, terminal, browser) →
sonucu raporlar. Multi-turn conversation ile iteratif çalışır.

### Mimari

```
┌──────────────────────────────────────────────────────┐
│  CLI / Chat Interface                                │
│  Kullanıcı doğal dilde görev verir                   │
└──────────────┬───────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────┐
│  Claude Agent SDK — Agent Loop                       │
│  System prompt + tool definitions + memory            │
│  Karar: hangi tool'u çağır, ne zaman dur              │
└──────┬──────────┬──────────┬─────────────────────────┘
       │          │          │
┌──────▼───┐ ┌───▼────┐ ┌───▼──────┐
│  GitHub  │ │ Shell  │ │ Browser  │
│  API     │ │ Exec   │ │ (Computer│
│  Tool    │ │ Tool   │ │  Use)    │
└──────────┘ └────────┘ └──────────┘
```

### Ne öğretir?

| Kavram | Bu Projede Nasıl Öğrenilir |
|---|---|
| **Claude API** | Tool use, structured output, system prompt design |
| **Agent SDK** | Custom agent loop: observe → think → act → repeat |
| **Tool definitions** | JSON schema ile tool tanımlama, Claude'un doğru tool'u seçmesi |
| **Multi-turn** | Conversation memory, context window yönetimi |
| **Computer use** | Browser automation ile web sayfalarında işlem yapma |
| **Structured output** | JSON response format zorlama, type-safe çıktı |

### Mülakatta Anlatılacak Kararlar
| Soru | Cevap |
|------|-------|
| Neden Claude SDK (LangChain değil)? | Daha düşük abstraction, tam kontrol. LangChain öğrendik, şimdi framework'süz de yapabildiğimizi gösteriyoruz. |
| Computer use ne zaman mantıklı? | API olmayan sistemlerle entegrasyon. Legacy UI'lar, web dashboard'lar. |
| Agent loop nasıl kontrol edilir? | Max iteration, token budget, tool whitelist — otonom ama sınırlı. |

---

## Proje 7: IdentityLab

**Repo:** `IdentityLab` (oluşturulacak)
**Odak:** Enterprise Identity & Access Management — Keycloak, OAuth2/OIDC, RBAC, MFA

> TelcoAgent'ta Keycloak overengineering'di — basit JWT yetti. Ama enterprise ortamda
> identity management kritik bir konu. Bu projede Keycloak'ı gerçekten ihtiyaç duyulan
> bir senaryoda derinlemesine öğreniyorsun.

### Senaryo: Multi-Tenant SaaS Kimlik Platformu

Bir SaaS uygulaması: birden fazla şirket (tenant) aynı platformu kullanıyor. Her tenant'ın
kendi kullanıcıları, rolleri ve izinleri var. Social login (Google, GitHub), MFA zorunluluğu,
ve API gateway üzerinden token validasyonu gerekiyor.

### Mimari

```
┌──────────────────────────────────────────────────────┐
│  React Frontend (admin-ui)                           │
│  Login → Keycloak hosted login page (OIDC)           │
│  Token refresh, silent SSO, logout                   │
└──────────────┬───────────────────────────────────────┘
               │ Bearer Token
┌──────────────▼───────────────────────────────────────┐
│  Kong / Traefik API Gateway                          │
│  OIDC plugin → Keycloak token introspection          │
│  Rate limiting per tenant                            │
└──────────────┬───────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────┐
│  FastAPI — Tenant Management API                     │
│  POST /tenants → yeni tenant (Keycloak realm/group)  │
│  GET  /users   → tenant-scoped kullanıcı listesi     │
│  PUT  /roles   → RBAC yönetimi                       │
└──────────────┬───────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────┐
│  Keycloak (Docker)                                   │
│  ├── Realm per tenant (veya single realm + groups)   │
│  ├── Identity Providers: Google, GitHub (social)     │
│  ├── MFA: TOTP + WebAuthn                            │
│  ├── Client Scopes: fine-grained permissions         │
│  ├── User Federation: LDAP bağlantısı (mock)         │
│  └── Admin REST API: programmatik yönetim            │
└──────────────┬───────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────┐
│  PostgreSQL — Keycloak + uygulama verisi             │
└──────────────────────────────────────────────────────┘
```

### Ne öğretir?

| Kavram | Bu Projede Nasıl Öğrenilir |
|---|---|
| **OAuth2 Flows** | Authorization Code + PKCE (frontend), Client Credentials (service-to-service) |
| **OIDC** | ID Token vs Access Token farkı, UserInfo endpoint, JWKS validation |
| **Multi-tenancy** | Realm-per-tenant vs single-realm-with-groups — trade-off'ları yaşayarak öğren |
| **RBAC** | Realm roles, client roles, composite roles — granüler izin modeli |
| **Social Login** | Google/GitHub identity provider entegrasyonu, account linking |
| **MFA** | TOTP setup flow, WebAuthn (passkeys), conditional MFA (admin-only) |
| **Token Management** | Access token lifetime, refresh token rotation, token revocation |
| **API Gateway + OIDC** | Kong/Traefik OIDC plugin ile gateway seviyesinde token validation |
| **Admin API** | Keycloak REST API ile programmatik realm/user/role yönetimi |
| **User Federation** | LDAP/Active Directory entegrasyonu (mock LDAP ile) |

### Mülakatta Anlatılacak Kararlar
| Soru | Cevap |
|------|-------|
| Neden Keycloak (Auth0/Firebase Auth değil)? | Self-hosted, tam kontrol. Enterprise'da data sovereignty kritik. Auth0 SaaS — vendor lock-in riski. |
| Realm-per-tenant mi, single realm mi? | Realm-per-tenant: tam izolasyon ama yönetim overhead'i fazla. Single realm + groups: daha kolay ama cross-tenant risk. Senaryoya göre seçim. |
| MFA neden zorunlu değil? | Conditional — sadece admin role'ü olanlar için. UX ile güvenlik dengesi. |
| PKCE neden? | Public client (SPA) için Authorization Code tek başına güvensiz — PKCE code interception attack'ı önler. |

### Neden ayrı proje?
TelcoAgent'ta Keycloak overengineering'di çünkü tek bir internal servis grubuydu —
simple JWT yeterdi. Bu projede ise multi-tenant, social login, MFA gibi gerçek
enterprise identity sorunları var — Keycloak burada doğru araç.

---

## Proje 8: ObservabilityLab

**Repo:** `ObservabilityLab` (oluşturulacak)
**Odak:** Distributed Observability — OpenTelemetry, Jaeger, Loki, Grafana Tempo

> TelcoAgent'ta Jaeger ve Loki sadece docker-compose'da duruyordu, gerçek instrumentation
> yoktu. Bu projede OpenTelemetry SDK ile gerçek distributed tracing ve log correlation
> yaparak observability'yi derinlemesine öğreniyorsun.

### Senaryo: Microservice Observability Platform

3 microservice'ten oluşan bir e-ticaret backend'i: Order → Payment → Notification.
Her servis OpenTelemetry ile instrument edilmiş. Bir istek geldiğinde trace ID tüm
servislerde takip ediliyor, loglar trace ile correlate ediliyor, metrikler
otomatik toplanıyor. Sorun olunca Grafana'da tek ekrandan trace + log + metric birlikte görülüyor.

### Mimari

```
┌──────────────────────────────────────────────────────┐
│  Load Generator (Locust)                             │
│  Farklı senaryolar: normal, yavaş, hatalı           │
└──────────────┬───────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────┐
│  Order Service (FastAPI)                             │
│  OTel auto-instrumentation                           │
│  → Payment Service çağırır (HTTP)                    │
│  → Notification Service'e event gönderir (Kafka)     │
└──────┬───────────────────────┬───────────────────────┘
       │ HTTP                  │ Kafka
┌──────▼──────┐         ┌──────▼──────┐
│  Payment    │         │  Notific.   │
│  Service    │         │  Service    │
│  (FastAPI)  │         │  (FastAPI)  │
│  OTel instr.│         │  OTel instr.│
└──────┬──────┘         └──────┬──────┘
       │                       │
┌──────▼───────────────────────▼───────────────────────┐
│  OpenTelemetry Collector (OTLP)                      │
│  Receives traces, metrics, logs from all services    │
│  Exports to multiple backends                        │
└──────┬───────────────┬───────────────┬───────────────┘
       │               │               │
┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
│  Jaeger     │ │  Loki       │ │  Prometheus │
│  (traces)   │ │  (logs)     │ │  (metrics)  │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │               │               │
┌──────▼───────────────▼───────────────▼───────────────┐
│  Grafana                                             │
│  Unified dashboard: Traces ↔ Logs ↔ Metrics          │
│  Trace → log correlation (traceID ile)               │
│  Alerting: latency p99 > 500ms, error rate > 5%      │
└──────────────────────────────────────────────────────┘
```

### Ne öğretir?

| Kavram | Bu Projede Nasıl Öğrenilir |
|---|---|
| **OpenTelemetry SDK** | Auto + manual instrumentation — span oluşturma, attribute ekleme, context propagation |
| **Distributed Tracing** | Trace ID bir servisten diğerine geçiyor — tüm call chain tek trace'de görünüyor |
| **OTel Collector** | Merkezi toplama noktası — receiver, processor, exporter pipeline'ı |
| **Jaeger** | Trace UI — waterfall view, service dependency graph, latency histogram |
| **Loki** | Structured logging — label bazlı sorgu, traceID ile log-trace correlation |
| **Log-Trace Correlation** | Log'a traceID inject et → Grafana'da log'dan trace'e, trace'den log'a tek tıkla geç |
| **Prometheus + OTel** | OTel metrics → Prometheus exporter → Grafana dashboard |
| **Custom Spans** | Business-level tracing — "ödeme işlemi", "stok kontrolü" gibi anlamlı span'ler |
| **Baggage / Context** | W3C Trace Context, baggage propagation (user_id, tenant_id taşıma) |
| **Sampling** | Head-based vs tail-based sampling — production'da trace volume kontrolü |

### Mülakatta Anlatılacak Kararlar
| Soru | Cevap |
|------|-------|
| Neden OTel (vendor SDK değil)? | Vendor-agnostic. Jaeger'dan Tempo'ya geçsen bile kod değişmez. |
| Jaeger vs Grafana Tempo? | Jaeger: standalone, kolay kurulum. Tempo: Grafana native, object storage backend, daha scalable. Her ikisini de deneyimlemek lazım. |
| Log-trace correlation neden önemli? | "500 Internal Server Error" gördüğünde trace'e bakıp hangi servisin hangi adımda patladığını anında bulursun. |
| Sampling neden? | Production'da her isteği trace'lemek çok pahalı. %10 head-based + hatalı istekleri %100 tail-based sampling ideal denge. |

### Neden ayrı proje?
TelcoAgent'ta Jaeger ve Loki docker-compose'da vardı ama hiçbir serviste gerçek
OpenTelemetry instrumentation yoktu — sadece infra kurulmuştu. Observability
gerçekten öğrenmek için instrument edilmiş servisler, real trace flow ve
log correlation lazım. Bu ancak odaklanmış bir projede olur.

---

## Opsiyonel Bir proje
Odak: Production-grade RAG Pipeline
├── Advanced Chunking (semantic, recursive, agentic)
├── Hybrid Search (vector + BM25 + metadata filtering)
├── Re-ranking (Cross-Encoder, LLM-based)
├── Query Transformation (HyDE, step-back prompting)
├── Evaluation Framework (RAGAS, TruLens)
└── Caching Layer (semantic cache with Redis)

## Öğrenme Sırası Önerisi

```
TelcoAgent (bitti) → TemporalLab → ResearchAgentLab → MLOpsLab → K8sLab → ObservabilityLab → IdentityLab
```

> **Neden bu sıra?**
> - TemporalLab: TelcoAgent'taki event-driven bilginin üzerine workflow orchestration ekler
> - ResearchAgentLab: LangGraph bilgisinin üzerine AutoGen + farklı DB'ler (Qdrant, MongoDB)
> - MLOpsLab: Agent bilgisinin üzerine model serving + operationalization
> - K8sLab: Tüm servisleri production'a taşıma — önceki projelerdeki servisleri deploy edersin
> - ObservabilityLab: K8s'ten sonra çünkü distributed tracing multi-service ortamda anlamlı
> - IdentityLab: En bağımsız proje — herhangi bir sırada yapılabilir ama sona koyduk

Her proje tamamlandıkça bu dosyaya "tamamlandı" işareti ekle ve
mülakatta anlatılacak kararları buraya yaz.

---

## Genel Mimari Kararlar (Tüm Projeler İçin Geçerli)

Bu kararlar her projede tekrar düşünmeden uygulanabilir:

| Karar | Tercih | Gerekçe |
|-------|--------|---------|
| Python async | `asyncio` + `async/await` her yerde | FastAPI, SQLAlchemy, aiokafka hepsi async |
| Config | `pydantic-settings` + `.env` | Type-safe, test edilebilir |
| Linting | `ruff` (120 char) | Hem lint hem format, hızlı |
| Type check | `mypy --strict` | Erken hata yakalama |
| Test | `pytest` + `pytest-asyncio` | Standart |
| DB migration | SQLAlchemy `create_all` (dev) → Alembic (prod) | Dev'de hızlı, prod'da güvenli |
| Secret management | `.env` (dev) → Kubernetes Secrets + Vault (prod) | Environment'a göre |
