# TelcoAgent Platform — Tüm Fazlar Eğitim Rehberi (Phase 1–4)

> Bu doküman, Phase 1'den Phase 4'e kadar yapılan tüm çalışmaları **kavramsal olarak** açıklayarak, okuduğunda "ne yapıldı, neden yapıldı, nasıl çalışıyor" sorularına net yanıt verebilmeni amaçlar.

---

## İçindekiler

### Phase 1 — Core Architecture & Infrastructure
1. [Phase 1 — Büyük Resim](#phase-1--büyük-resim)
2. [Docker Compose — 17 Servislik Altyapı](#docker-compose--17-servislik-altyapı)
3. [init-db.sql — Veritabanı Bootstrap](#init-dbsql--veritabanı-bootstrap)
4. [Async Database Utilities](#async-database-utilities)
5. [DDD Base Building Blocks](#ddd-base-building-blocks)
6. [Shared Configuration — Settings](#shared-configuration--settings)

### Phase 2 — Domain Microservices
7. [Phase 2 — Büyük Resim](#phase-2--büyük-resim)
8. [Customer Domain — DDD Derinlemesine](#customer-domain--ddd-derinlemesine)
9. [Billing Domain — Invoice Aggregate](#billing-domain--invoice-aggregate)
10. [Billing Value Objects — Money, Period, Status](#billing-value-objects--money-period-status)
11. [Billing Domain Service — Anomaly Detection](#billing-domain-service--anomaly-detection)
12. [CQRS Pattern — Command ve Query Ayrımı](#cqrs-pattern--command-ve-query-ayrımı)
13. [REST API Endpoints — FastAPI Routes](#rest-api-endpoints--fastapi-routes)
14. [ORM Models — SQLAlchemy + pgvector](#orm-models--sqlalchemy--pgvector)
15. [Outbox Pattern — Kafka Event Publishing](#outbox-pattern--kafka-event-publishing)
16. [Repository Pattern — Domain ↔ Infrastructure Köprüsü](#repository-pattern--domain--infrastructure-köprüsü)
17. [gRPC Proto Definitions](#grpc-proto-definitions)

### Phase 3 — CustomerSupportAgent
18. [Phase 3 — Büyük Resim](#phase-3--büyük-resim)
19. [LangGraph ReAct Pattern Nedir?](#langgraph-react-pattern-nedir)
20. [Agent'ın Tool Sistemi](#agentın-tool-sistemi)
21. [Redis Short-Term Memory](#redis-short-term-memory)
22. [Kafka Consumer — Event-Driven Agent Tetikleme](#kafka-consumer--event-driven-agent-tetikleme)
23. [Prometheus Metrikleri — Observability](#prometheus-metrikleri--observability)
24. [Agent Akışı: Uçtan Uca Senaryo](#agent-akışı-uçtan-uca-senaryo)

### Phase 4 — MCP Layer
25. [Phase 4 — Büyük Resim](#phase-4--büyük-resim)
26. [MCP (Model Context Protocol) Nedir?](#mcp-model-context-protocol-nedir)
27. [MCP Server'lar: Tool vs Resource](#mcp-serverlar-tool-vs-resource)
28. [MCP Client — Dynamic Tool Discovery](#mcp-client--dynamic-tool-discovery)
29. [OpenAPI → MCP Auto-Generator](#openapi--mcp-auto-generator)
30. [REST vs gRPC vs MCP Karşılaştırma](#rest-vs-grpc-vs-mcp-karşılaştırma)

### Genel
31. [Tüm Fazların Birlikte Çalışması](#tüm-fazların-birlikte-çalışması)
32. [Scripts — Seed Data & Benchmark](#scripts--seed-data--benchmark)
33. [Unit Tests — Test Altyapısı](#unit-tests--test-altyapısı)
34. [Anahtar Mimari Kararlar Özet Tablosu](#anahtar-mimari-kararlar-özet-tablosu)

---

# PHASE 1 — Core Architecture & Infrastructure

---

## Phase 1 — Büyük Resim

Phase 1'in amacı **projenin temelini atmak**tır. DDD yapı taşlarını (base class'lar), paylaşılan altyapıyı (settings, database, events) ve tüm servislerin bağlı olacağı Docker Compose stack'ini kurar.

### Ne Üretildi?

```
shared/
├── config/
│   └── settings.py           ← Merkezi konfigürasyon (Pydantic Settings)
├── events/
│   └── base.py               ← DomainEvent base class
├── models/
│   └── base.py               ← ValueObject, Entity, AggregateRoot
└── utils/
    └── database.py            ← SQLAlchemy async engine + session factory

infrastructure/
├── docker/
│   └── init-db.sql            ← PostgreSQL startup scripti (outbox schema)
├── keycloak/
│   └── telco-agents-realm.json← Keycloak realm konfigürasyonu
├── monitoring/
│   └── prometheus/
│       └── prometheus.yml     ← Scrape target'ları
└── grpc/                      ← Proto definitions (gelecek kullanım)

docker-compose.yml             ← 14 servislik altyapı
pyproject.toml                 ← Bağımlılık yönetimi
```

### Temel Felsefe

Phase 1'de hiçbir iş mantığı (business logic) yazılmaz. Sadece **iskelet + altyapı** kurulur. Neden?

- Servislerin hepsinin kullanacağı ortak kodlar (base class, settings) önce hazır olmalı
- Docker Compose ile tüm dış bağımlılıklar (DB, Kafka, Redis...) **tek komutla** ayağa kalkmalı
- İlerideki fazlar bu temelin üzerine inşa eder

---

## Docker Compose — 17 Servislik Altyapı

`docker compose up -d` komutu ile tek seferde tüm altyapı ayağa kalkar. Her servis neden var?

### Servis Tablosu

| Servis | Image | Port | Neden Var? |
|--------|-------|------|-----------|
| **postgres** | `pgvector/pgvector:pg16` | 5432 | Ana veritabanı + vector embeddings (pgvector eklentisi) |
| **redis** | `redis:7-alpine` | 6379 | Agent short-term memory, cache |
| **mongodb** | `mongo:7` | 27017 | Episodic memory (agent karar geçmişi) |
| **qdrant** | `qdrant/qdrant` | 6333 | Semantic search (FAQ, benzer vaka arama) |
| **zookeeper** | `cp-zookeeper:7.7.1` | 2181 | Kafka cluster koordinasyonu (broker yönetimi, lider seçimi) |
| **kafka** | `cp-kafka:7.7.1` | 9092 | Event streaming (domain events) |
| **schema-registry** | `cp-schema-registry` | 8081 | Avro schema yönetimi |
| **kafka-ui** | `kafka-ui` | 8082 | Kafka topic'lerini görsel izleme |
| **keycloak** | `keycloak:26.0` | 8080 | Identity & Access Management (OAuth2.0) |
| **temporal** | `temporalio/auto-setup` | 7233 | Fault-tolerant workflow engine |
| **temporal-ui** | `temporalio/ui` | 8083 | Temporal workflow izleme |
| **customer-service** | build | 8001 | Customer bounded context REST API (CQRS + Outbox) |
| **billing-service** | build | 8002 | Billing bounded context REST API (CQRS + Outbox) |
| **traefik** | `traefik:v3.2` | 80/8084 | API Gateway (routing, load balancing) |
| **prometheus** | `prom/prometheus` | 9090 | Metrik toplama |
| **grafana** | `grafana/grafana` | 3000 | Dashboard ve görselleştirme |
| **loki** | `grafana/loki` | 3100 | Log agregasyonu |
| **jaeger** | `jaegertracing/all-in-one` | 16686 | Distributed tracing |

### Kafka ZooKeeper Modu

Kafka, **ZooKeeper** ile çalışır. ZooKeeper cluster koordinasyonunu üstlenir — broker kaydı, lider seçimi ve metadata yönetimi:

```yaml
# ZooKeeper servisi
zookeeper:
  environment:
    ZOOKEEPER_CLIENT_PORT: 2181

# Kafka, ZooKeeper'a bağlanır
kafka:
  depends_on:
    zookeeper:
      condition: service_healthy
  environment:
    KAFKA_BROKER_ID: 1
    KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
```

**Healthcheck:** ZooKeeper'ın ayakta olup olmadığı `echo ruok | nc localhost 2181` komutu ile test edilir. `imok` cevabı döndüğünde sağlıklıdır.

### Healthcheck Pattern

Her servisin healthcheck'i var. Bu, bağımlı servislerin hazır olmadan başlamamasını sağlar:

```yaml
postgres:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U telco"]
    interval: 5s

kafka:
  healthcheck:
    test: ["CMD", "kafka-topics", "--bootstrap-server", "localhost:9092", "--list"]
    interval: 10s

# Bağımlılık:
customer-support-agent:
  depends_on:
    postgres:
      condition: service_healthy   # postgres sağlıklı olana kadar bekleme
    kafka:
      condition: service_healthy
```

---

## init-db.sql — Veritabanı Bootstrap

PostgreSQL ilk ayağa kalktığında çalışan init script'i. Her bounded context için **ayrı schema** oluşturur:

```sql
-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";   -- UUID üretimi
CREATE EXTENSION IF NOT EXISTS "vector";       -- pgvector (embedding depolama)

-- Her bounded context kendi schema'sında yaşar
CREATE SCHEMA IF NOT EXISTS customer;
CREATE SCHEMA IF NOT EXISTS billing;
CREATE SCHEMA IF NOT EXISTS network;
CREATE SCHEMA IF NOT EXISTS campaign;
CREATE SCHEMA IF NOT EXISTS outbox;            -- paylaşılan outbox pattern
CREATE SCHEMA IF NOT EXISTS keycloak;          -- Keycloak identity management
```

### Outbox Tablosu

```sql
CREATE TABLE IF NOT EXISTS outbox.events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aggregate_type  VARCHAR(255) NOT NULL,
    aggregate_id    VARCHAR(255) NOT NULL,
    event_type      VARCHAR(255) NOT NULL,
    payload         JSONB NOT NULL,
    published       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at    TIMESTAMPTZ
);

-- Sadece yayınlanmamış event'leri hızlıca bulmak için partial index
CREATE INDEX IF NOT EXISTS idx_outbox_unpublished
    ON outbox.events (created_at)
    WHERE published = FALSE;
```

**Neden ayrı schema?** Her bounded context'in tabloları kendi namespace'inde yaşar — `customer.customers`, `billing.invoices` gibi. Bu sayede isim çakışması olmaz ve schema seviyesinde izolasyon sağlanır.

---

## Async Database Utilities

`shared/utils/database.py`, tüm servislerin paylaştığı SQLAlchemy async engine ve session factory'sini tanımlar:

```python
# Async engine — connection pool ile
engine = create_async_engine(
    settings.database_url,
    echo=False,         # SQL loglamasını kapat (production'da performans)
    pool_size=10,       # sabit 10 connection
    max_overflow=20,    # yoğun dönemde +20 ekstra
)

# Session factory — her request'te yeni session
AsyncSessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # commit sonrası nesneler geçersiz olmasın
)
```

### FastAPI Dependency Injection

```python
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()    # başarılıysa commit
        except Exception:
            await session.rollback()  # hata olursa rollback
            raise
```

**Nasıl kullanılır?** FastAPI endpoint'lerinde `Depends(get_db_session)` ile inject edilir:

```python
@router.get("/")
async def list_customers(
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    # session otomatik olarak inject edilir, commit/rollback otomatik
```

---

## DDD Base Building Blocks

Tüm domain modelleri 3 temel yapı taşı üzerine inşa edilir. Bu yapı taşları `shared/models/base.py`'de tanımlıdır.

### 1. ValueObject — Değerce Eşitlik

```python
class ValueObject(BaseModel):
    """Immutable — değişmez, kimliksiz, değerine göre karşılaştırılır."""
    model_config = {"frozen": True}  # Pydantic ile immutable
```

**Gerçek hayat örneği:** Bir telefon numarası `+905551234567`. İki farklı nesnede aynı numara varsa, bunlar **eşittir**. Numaranın bir UUID'si yoktur — değeri onun kimliğidir.

**Projede:**
- `PhoneNumber(country_code="+90", number="5551234567")`
- `Address(city="İstanbul", district="Kadıköy", ...)`
- `Money(amount=189.90, currency="TRY")`
- `BillingPeriod(year=2026, month=2)`

### 2. Entity — Kimlik + Değişebilir Durum

```python
class Entity(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = ...
    updated_at: datetime = ...
```

Entity'nin bir **kimliği** (UUID) vardır. İki entity aynı verilere sahip olsa bile, UUID'leri farklıysa **farklı** entity'lerdir.

### 3. AggregateRoot — Tutarlılık Sınırı

```python
class AggregateRoot(Entity):
    _domain_events: list[DomainEvent] = PrivateAttr(default_factory=list)

    def add_event(self, event: DomainEvent) -> None:
        self._domain_events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        events = self._domain_events.copy()
        self._domain_events.clear()   # → topla ve temizle
        return events
```

**AggregateRoot, DDD'nin en önemli kavramıdır.** Bir Aggregate:
- **Tutarlılık sınırı** çizer — tüm iş kuralları bu sınır içinde uygulanır
- **Domain event'leri biriktirir** — işlem tamamlandığında event'ler toplanıp outbox'a yazılır
- **Dışarıdan sadece Aggregate Root üzerinden erişilir** — içindeki entity'lere direkt erişim yasaktır

### 4. DomainEvent — Olaylar

```python
class DomainEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str           # "customer.created"
    aggregate_id: str          # hangi aggregate'e ait
    aggregate_type: str        # "Customer"
    occurred_at: datetime      # ne zaman oldu
    version: int = 1           # schema version

    model_config = {"frozen": True}  # event'ler immutable
```

Event'ler **geçmişte olan** bir şeyi ifade eder ("CustomerCreated", "InvoicePaid"). Bir kez oluştuktan sonra **değiştirilemezler** (immutable).

### Bu 4 Kavramın İlişkisi

```
AggregateRoot (Customer)
    │
    ├── name: str                        ← basit alan
    ├── phone_number: PhoneNumber        ← ValueObject
    ├── segment: CustomerSegment         ← ValueObject (enum)
    │
    ├── create() → CustomerCreated       ← factory method + event
    ├── change_segment() → SegmentChanged← business method + event
    └── file_complaint() → ComplaintFiled← business method + event
         │
         └── _domain_events: [...]       ← birikmiş event listesi
```

---

## Shared Configuration — Settings

Tüm servisler aynı `Settings` class'ını kullanır. Environment variable'lardan otomatik yüklenir:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",         # .env dosyasından oku
        case_sensitive=False,    # POSTGRES_HOST = postgres_host
        extra="ignore",          # bilinmeyen env var'ları hata vermez
    )

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    ...

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:..."
```

**Neden `pydantic-settings`?**
- Tip güvenliği (port'un int olması garanti)
- `.env` dosyasından otomatik yükleme
- Default değerler (local dev için)
- `@lru_cache` ile singleton pattern — Settings nesnesi bir kez oluşturulur

---

# PHASE 2 — Domain Microservices

---

## Phase 2 — Büyük Resim

Phase 2'de **Customer Service** ve **Billing Service** olmak üzere 2 domain mikroservisi oluşturulur. Her ikisi de Phase 1'de kurulan DDD yapı taşlarını kullanır.

### Ne Üretildi?

```
services/
├── customer/
│   ├── api/
│   │   ├── main.py       ← FastAPI app
│   │   └── routes.py     ← REST endpoint'leri
│   ├── application/
│   │   ├── commands/
│   │   │   └── handlers.py ← CQRS write side
│   │   └── queries/
│   │       └── handlers.py ← CQRS read side
│   ├── domain/
│   │   ├── model/
│   │   │   ├── customer.py      ← Aggregate Root
│   │   │   ├── value_objects.py ← PhoneNumber, CustomerSegment, SubscriptionPlan
│   │   │   └── events.py       ← 4 domain event
│   │   ├── repository.py       ← Abstract repository interface
│   │   └── services.py         ← Domain services
│   └── infrastructure/
│       ├── postgres_repository.py ← Concrete repository
│       ├── kafka_publisher.py     ← Outbox Pattern
│       └── orm_models.py         ← SQLAlchemy ORM modelleri
│
├── billing/
│   ├── api/                ← FastAPI app + routes
│   ├── application/        ← CQRS handlers
│   ├── domain/
│   │   └── model/
│   │       ├── invoice.py       ← Invoice Aggregate Root
│   │       ├── value_objects.py ← Money, BillingPeriod, InvoiceStatus
│   │       └── events.py       ← 6 domain event
│   └── infrastructure/     ← PostgreSQL repository
│
├── network/                ← Skeleton (gelecek fazlar)
└── campaign/               ← Skeleton (gelecek fazlar)
```

### Katmanlı Mimari

Her servis 4 katmandan oluşur:

```
┌────────────────────────────────────┐
│            API Layer               │ ← FastAPI routes, HTTP request/response
│   routes.py, main.py               │
├────────────────────────────────────┤
│         Application Layer          │ ← CQRS handlers, use case orchestration
│   commands/, queries/              │ ← İş akışını yönetir, domain'i çağırır
├────────────────────────────────────┤
│           Domain Layer             │ ← Aggregate Root, Value Objects, Events
│   model/, repository.py(abc),      │ ← SIFIR altyapı bağımlılığı (pure Python)
│   services.py                      │
├────────────────────────────────────┤
│       Infrastructure Layer         │ ← PostgreSQL, Kafka, ORM
│   postgres_repository.py,          │ ← Domain'in abstract'ını implement eder
│   kafka_publisher.py, orm_models.py│
└────────────────────────────────────┘
```

**Kurallar:**
- Domain katmanı **hiçbir** altyapıya bağımlı değildir (SQLAlchemy import yok, Kafka yok)
- Domain katmanı sadece `shared/models/base.py` ve `shared/events/base.py`'yi bilir
- Bağımlılık yönü her zaman **dışarıdan içeriye** doğrudur (Infrastructure → Domain, asla tersi)

---

## Customer Domain — DDD Derinlemesine

### Aggregate Root: Customer

```python
class Customer(AggregateRoot):
    name: str
    phone_number: PhoneNumber              # ValueObject
    email: str | None = None
    segment: CustomerSegment = CustomerSegment.NEW    # Enum ValueObject
    subscription_plan: SubscriptionPlan     # Enum ValueObject
    clv_score: float = 0.0
    is_active: bool = True
```

### Factory Method Pattern

Müşteri oluştururken `__init__` yerine `Customer.create()` kullanılır. **Neden?**

```python
@classmethod
def create(cls, name, phone_number, email, subscription_plan):
    customer = cls(name=name, phone_number=phone_number, ...)

    # ⬇️ Factory method event'i EKLEMEYİ GARANTİ eder
    customer.add_event(
        CustomerCreated(
            aggregate_id=str(customer.id),
            name=name,
            ...
        )
    )
    return customer
```

Eğer `Customer(name=..., ...)` direkt çağırsaydın, event eklemeyi **unutabilirdin**. Factory method, iş kuralıyla event yayınlamayı **atomik** hale getirir.

### Business Method'lar

Her iş eylemi hem state'i değiştirir hem event üretir:

```python
def change_segment(self, new_segment, reason):
    if new_segment == self.segment:
        return                    # ← invariant kontrolü (aynı segment'e geçiş yok)
    old_segment = self.segment
    self.segment = new_segment    # ← state değişikliği
    self.add_event(               # ← event üretimi
        CustomerSegmentChanged(old_segment=..., new_segment=..., reason=...)
    )

def file_complaint(self, complaint_type, description, priority):
    self.add_event(
        ComplaintFiled(complaint_type=..., priority=...)
    )
```

### Value Objects Detay

| Value Object | Tip | Alanlar | Rolü |
|-------------|-----|---------|------|
| `PhoneNumber` | Class | `country_code`, `number` | Türk telefon formatı, `__str__` → `+905551234567` |
| `Address` | Class | `city`, `district`, `postal_code`, `full_address` | Immutable adres |
| `CustomerSegment` | StrEnum | `platinum, gold, silver, bronze, new, churning` | Müşteri segmenti |
| `SubscriptionPlan` | StrEnum | `prepaid_basic, postpaid_premium, fiber_home, ...` | Abonelik planı |

### Domain Events

| Event | Ne Zaman Fırlatılır? | Tükettici |
|-------|---------------------|-----------|
| `CustomerCreated` | Yeni müşteri kaydı | Audit log, campaign service |
| `CustomerSegmentChanged` | Segment upgrade/downgrade | Campaign agent (kişiye özel teklif) |
| `ComplaintFiled` | Şikayet açılması | **CustomerSupportAgent** (Phase 3) |
| `CustomerChurnRiskDetected` | ML model tetiklemesi | Campaign agent (retention) |

### Domain Service: Segmentation

Domain logic'in aggregate'e sığmadığı durumlar için:

```python
class CustomerSegmentationService:
    @staticmethod
    def calculate_segment(clv_score: float, months_active: int) -> CustomerSegment:
        if clv_score >= 800 and months_active >= 24:
            return CustomerSegment.PLATINUM
        elif clv_score >= 500 and months_active >= 12:
            return CustomerSegment.GOLD
        elif clv_score >= 200 and months_active >= 6:
            return CustomerSegment.SILVER
        elif months_active < 3:
            return CustomerSegment.NEW
        else:
            return CustomerSegment.BRONZE
```

**Neden Domain Service?** Segmentation kararı birden fazla veriye (CLV score + months active) bağlı. Bu mantık tek bir Customer entity'sine ait değil — **domain-level** bir karardır.

### Churn Risk Assessment

```python
@staticmethod
def assess_churn_risk(customer, complaint_count, days_since_last_usage) -> float:
    risk = 0.0
    if complaint_count >= 3:        risk += 0.3
    if days_since_last_usage >= 30: risk += 0.4
    if customer.segment == CustomerSegment.CHURNING: risk += 0.2
    return min(risk, 1.0)  # max 1.0
```

Bu basit rule-based risk skoru, ilerideki fazlarda ML modeli ile değiştirilecek placeholder'dır.

---

## Billing Domain — Invoice Aggregate

Billing Domain'in Aggregate Root'u `Invoice`'dur. Customer'a benzer pattern:

### Invoice Aggregate Root

```python
class Invoice(AggregateRoot):
    customer_id: str
    period: BillingPeriod          # ValueObject (year, month)
    amount: Money                   # ValueObject (amount, currency)
    status: InvoiceStatus           # Enum: DRAFT, ISSUED, PAID, OVERDUE, DISPUTED, CANCELLED
    line_items: list[dict]          # Fatura kalemleri
    dispute_status: DisputeStatus   # OPEN, RESOLVED, REJECTED
```

### Business Method'ları

| Method | İnvariant Kontrolü | Event |
|--------|-------------------|-------|
| `create()` | — | `InvoiceCreated` |
| `mark_paid()` | Status ISSUED veya OVERDUE olmalı | `InvoicePaid` |
| `flag_anomaly()` | — | `BillingAnomalyFound` |
| `open_dispute()` | Zaten açık dispute olmamalı | `DisputeOpened` |
| `resolve_dispute()` | Açık dispute olmalı | `DisputeResolved` |

### İnvariant Kontrolü Nedir?

Aggregate Root'un en önemli görevi **iş kurallarını ihlal edecek durumları engellemek**tir:

```python
def mark_paid(self):
    if self.status not in (InvoiceStatus.ISSUED, InvoiceStatus.OVERDUE):
        raise ValueError(f"Cannot pay invoice in status: {self.status}")
    # ← DRAFT veya CANCELLED bir faturayı ödeyemezsin

def open_dispute(self, reason):
    if self.dispute_status == DisputeStatus.OPEN:
        raise ValueError("Dispute already open")
    # ← Aynı faturaya 2 kez dispute açamazsın
```

---

## Billing Value Objects — Money, Period, Status

### Money — Operator Overloading ile Para Birimi

```python
class Money(ValueObject):
    amount: Decimal           # Decimal → hassas para hesabı
    currency: Currency = Currency.TRY

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def __str__(self) -> str:
        return f"{self.amount:.2f} {self.currency.value}"  # "189.90 TRY"
```

**Neden `Decimal`?** `float` ile `0.1 + 0.2 = 0.30000000000000004` olur. Para hesaplarında bu kabul edilemez. `Decimal` tam hassasiyet sağlar.

**Neden operator overloading?** `money1 + money2` yazabilmek kodun okunabilirliğini artırır. Ama farklı currency'leri toplamak hata verir — bu bir **domain invariant**.

### BillingPeriod

```python
class BillingPeriod(ValueObject):
    year: int
    month: int   # 1-12

    @property
    def label(self) -> str:
        return f"{self.year}-{self.month:02d}"  # "2026-02"
```

### Enum'lar

| Enum | Değerler | Nerede Kullanılır? |
|------|---------|---|
| `Currency` | TRY, USD, EUR | `Money.currency` |
| `InvoiceStatus` | draft, issued, paid, overdue, disputed, cancelled | `Invoice.status` |
| `DisputeStatus` | open, under_review, resolved, rejected | `Invoice.dispute_status` |

---

## Billing Domain Service — Anomaly Detection

```python
class BillingAnomalyService:
    ANOMALY_THRESHOLD_PERCENT = 30.0

    @staticmethod
    def detect_anomaly(current_amount: Money, historical_amounts: list[Money]) -> dict:
        avg = sum(m.amount for m in historical_amounts) / len(historical_amounts)
        deviation_pct = ((current_amount.amount - avg) / avg) * 100

        result = {
            "current_amount": str(current_amount.amount),
            "historical_average": str(round(avg, 2)),
            "deviation_percent": float(deviation_pct),
            "anomaly_detected": abs(deviation_pct) > 30.0,
        }
        if result["anomaly_detected"]:
            result["recommendation"] = "Faturada anormal sapma tespit edildi."
        return result
```

**Bu ne yapıyor?** Son faturayı geçmiş ortalamayla karşılaştırır. %30'dan fazla sapma varsa → anomali. Bu mantık MCP server'daki `calculate_billing_anomaly` tool'unun da temelini oluşturur.

---

## CQRS Pattern — Command ve Query Ayrımı

CQRS = **C**ommand **Q**uery **R**esponsibility **S**egregation (Komut-Sorgu Sorumluluk Ayrımı)

### Temel Fikir

```
Yazma işlemleri (POST, PUT, DELETE)     →   Command Handlers
                                             │
                                             ▼
                                        Domain Model
                                        (aggregate, events)
                                             │
                                             ▼
                                        PostgreSQL

Okuma işlemleri (GET)                   →   Query Handlers
                                             │
                                             ▼
                                        ORM Modeller (direkt)
                                             │
                                             ▼
                                        DTO (Data Transfer Object)
```

### Command Handler Örneği: Müşteri Kayıt

```python
class CustomerCommandHandlers:
    def __init__(self, session):
        self._repo = PostgresCustomerRepository(session)
        self._outbox = OutboxRepository(session)

    async def handle_register(self, cmd: RegisterCustomerCommand):
        # 1. Value Object oluştur
        phone = PhoneNumber(number=cmd.phone_number)
        plan = SubscriptionPlan(cmd.subscription_plan)

        # 2. Aggregate Root factory method → state + event
        customer = Customer.create(name=cmd.name, phone_number=phone, ...)

        # 3. Repository ile kaydet
        await self._repo.save(customer)

        # 4. Event'leri outbox'a yaz (AYNI transaction!)
        for event in customer.collect_events():
            await self._outbox.save(event)

        return customer
```

### Query Handler Örneği: Müşteri Getir

```python
class CustomerQueryHandlers:
    async def get_customer(self, customer_id: str) -> CustomerDTO | None:
        result = await self._session.get(CustomerORM, uid)
        return self._to_dto(result) if result else None

    async def list_customers(self, skip=0, limit=50) -> list[CustomerDTO]:
        stmt = select(CustomerORM).where(CustomerORM.is_active == True)
        results = await self._session.scalars(stmt)
        return [self._to_dto(r) for r in results.all()]
```

### DTO (Data Transfer Object) Nedir?

Domain modelini **direkt dışarıya dönemezsin** çünkü:
- İç eventler, private state gibi bilgiler sızar
- Okuma ve yazma modelleri farklı olabilir
- API response formatı domain modelden bağımsız olmalı

```python
@dataclass
class CustomerDTO:
    id: str               # UUID → str dönüşümü
    name: str
    phone_number: str     # PhoneNumber → str dönüşümü
    email: str | None
    segment: str          # Enum → str dönüşümü
    ...
```

### CQRS'in Faydası Ne?

| Avantaj | Açıklama |
|---------|----------|
| **Ayrı optimizasyon** | Okuma için indeks, yazma için transaction |
| **Basitlik** | Her handler tek bir iş yapar |
| **Scalability** | Okuma trafiği fazlaysa sadece query tarafını ölçekle |
| **Güvenlik** | Yazma işlemleri sadece command handler üzerinden geçer |

---

## Outbox Pattern — Kafka Event Publishing

**Problem:** Veritabanına veri yazıyorsun ve aynı anda Kafka'ya event gönderiyorsun. İkisi farklı sistemler. Ya DB yazılır ama Kafka başarısız olursa? Ya da Kafka'ya gönderilir ama DB transaction rollback olursa?

**Çözüm:** Outbox Pattern — event'leri DB'ye yaz (aynı transaction), sonra ayrı bir süreç okuyup Kafka'ya göndersin.

### Akış

```
1. Command Handler:
   ┌─── Aynı DB Transaction ───────────────────────┐
   │  customer_repo.save(customer)                  │
   │  outbox_repo.save(CustomerCreated event)       │   ← outbox.events tablosuna yazar
   └────────────────────────────────────────────────┘
       ↓ commit

2. Outbox Poller (FastAPI lifespan'da background task olarak çalışır, her 5 saniyede bir):
   SELECT * FROM outbox.events WHERE published = FALSE
       ↓
   kafka_producer.send(topic, event)
       ↓
   UPDATE outbox.events SET published = TRUE
```

### Outbox Tablosu

```sql
CREATE TABLE outbox.events (
    id             UUID PRIMARY KEY,
    aggregate_type TEXT,           -- "Customer"
    aggregate_id   TEXT,           -- müşteri UUID
    event_type     TEXT,           -- "customer.created"
    payload        JSONB,          -- event içeriği
    published      BOOLEAN DEFAULT FALSE,
    created_at     TIMESTAMP DEFAULT NOW(),
    published_at   TIMESTAMP
);
```

### Topic Mapping

```python
self._topic_map = {
    "customer.created":           "telco.customers.created",
    "customer.segment_changed":   "telco.customers.segment_changed",
    "customer.complaint_filed":   "telco.customers.complaints",
    "customer.churn_risk_detected": "telco.customers.churn_risk",
}
```

Her domain event tipi, ilgili Kafka topic'ine yönlendirilir. Bu sayede farklı consumer'lar sadece ilgilendikleri topic'i dinler.

### Neden Direkt Kafka'ya Göndermiyoruz?

| Yaklaşım | Problem |
|-----------|---------|
| Direkt Kafka | DB commit olur ama Kafka fail ederse → event kaybolur |
| Kafka önce | Kafka send olur ama DB rollback → phantom event |
| **Outbox** | İkisi aynı DB transaction'da → garanti tutarlılık |

---

## REST API Endpoints — FastAPI Routes

Customer Service 5 REST endpoint sunar. Her endpoint, ilgili CQRS handler'ı çağırır:

| HTTP | Endpoint | Handler | Açıklama |
|------|---------|---------|----------|
| `POST` | `/v1/customers/` | `handle_register` (Command) | Yeni müşteri kaydı |
| `GET` | `/v1/customers/` | `list_customers` (Query) | Aktif müşterileri listele |
| `GET` | `/v1/customers/{id}` | `get_customer` (Query) | ID ile müşteri getir |
| `POST` | `/v1/customers/{id}/complaints` | `handle_file_complaint` (Command) | Şikayet aç → Kafka'ya event gönderir |
| `GET` | `/v1/customers/{id}/complaints` | `get_complaints` (Query) | Müşterinin şikayetlerini listele |
| `PATCH` | `/v1/customers/{id}/segment` | `handle_change_segment` (Command) | Segment değiştir |

### Request → Command → Domain → Outbox Akışı

```python
@router.post("/{customer_id}/complaints", status_code=201)
async def file_complaint(
    customer_id: UUID,
    body: FileComplaintRequest,                              # Pydantic request model
    session: Annotated[AsyncSession, Depends(get_db_session)], # DI
):
    handlers = CustomerCommandHandlers(session)
    await handlers.handle_file_complaint(
        FileComplaintCommand(
            customer_id=str(customer_id),
            complaint_type=body.complaint_type,
            ...
        )
    )
    return {"status": "complaint filed"}
```

**Akış:** HTTP Request → Pydantic validation → Command oluştur → Handler çağır → Domain method → Event üret → Outbox'a yaz → DB commit → Response.

---

## ORM Models — SQLAlchemy + pgvector

ORM modelleri, domain modellerinden **tamamen ayrıdır**. Infrastructure katmanında yaşarlar:

```python
class CustomerORM(Base):
    __tablename__ = "customers"
    __table_args__ = {"schema": "customer"}  # ← bounded context schema

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    phone_number: Mapped[str] = mapped_column(String(20), unique=True)
    segment: Mapped[str] = mapped_column(String(50), default="new")

    # Value Object → JSONB olarak saklanır
    address: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # 🔑 pgvector — müşteri profil embedding'i (1536 boyut)
    profile_embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1536), nullable=True
    )
```

### pgvector Nedir?

PostgreSQL'e vector veri tipi ve similarity search ekleyen bir extensiondur. `Vector(1536)` kolonu, OpenAI embedding boyutunda bir vektör tutar.

**Ne İşe Yarar?** İlerideki fazlarda "Bu müşteriye en benzer profildeki müşteriler kim?" sorusunu **SQL ile** yanıtlayabilirsin:

```sql
SELECT * FROM customer.customers
ORDER BY profile_embedding <=> '[0.1, 0.2, ...]'  -- cosine distance
LIMIT 5;
```

### Complaint ORM

```python
class ComplaintORM(Base):
    __tablename__ = "complaints"
    __table_args__ = {"schema": "customer"}

    customer_id: Mapped[uuid.UUID]  # FK mantığı (explicit FK yok, domain rule)
    complaint_type: Mapped[str]      # billing | network | service | general
    priority: Mapped[str]            # low | medium | high | critical
    status: Mapped[str]              # open | in_progress | resolved
    resolution: Mapped[str | None]   # çözüm açıklaması
```

### CustomerVectorStore — pgvector ile Similarity Search

`vector_store.py`, pgvector kolonunu kullanarak benzer müşteri profili arama yapar:

```python
class CustomerVectorStore:
    async def upsert_profile_embedding(self, customer_id: str, embedding: list[float]):
        """1536-boyut embedding'i müşteri kaydına yazar."""
        await self._session.execute(text("""
            UPDATE customer.customers
            SET profile_embedding = :embedding::vector
            WHERE id = :customer_id::uuid
        """), {"customer_id": customer_id, "embedding": str(embedding)})

    async def find_similar_customers(self, embedding: list[float], limit: int = 5):
        """Cosine distance ile en benzer müşterileri bulur."""
        result = await self._session.execute(text("""
            SELECT id, name, segment, clv_score,
                   1 - (profile_embedding <=> :embedding::vector) AS similarity
            FROM customer.customers
            WHERE profile_embedding IS NOT NULL
            ORDER BY profile_embedding <=> :embedding::vector
            LIMIT :limit
        """), {"embedding": str(embedding), "limit": limit})
```

**`<=>` operatörü** pgvector'ün cosine distance operatörüdür. `1 - distance = similarity` ile benzerlik skoru (0-1) hesaplanır.

**Kullanım senaryoları:**
- "Bu müşteriye en benzer profildeki 5 müşteri kim?" → churn prediction, cross-sell
- "Bu şikayete benzer geçmiş şikayetler neler?" → agent'a bağlam sağlama

---

## Repository Pattern — Domain ↔ Infrastructure Köprüsü

### Abstract Repository (Domain Katmanı)

```python
class CustomerRepository(ABC):
    @abstractmethod
    async def save(self, customer: Customer) -> Customer: ...

    @abstractmethod
    async def find_by_id(self, customer_id: UUID) -> Customer | None: ...

    @abstractmethod
    async def find_by_phone(self, phone_number: str) -> Customer | None: ...
```

**Neden abstract?** Domain katmanı PostgreSQL'i bilmemeli. Yarın MongoDB'ye geçersen sadece infrastructure katmanında yeni bir implementation yazarsın — domain kodu hiç değişmez.

### Concrete Repository (Infrastructure Katmanı)

```python
class PostgresCustomerRepository(CustomerRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, customer: Customer) -> Customer:
        existing = await self._session.get(CustomerORM, customer.id)
        if existing:
            await self._session.execute(update(...))  # upsert
        else:
            self._session.add(CustomerORM(...))       # insert
        return customer

    async def find_by_id(self, customer_id) -> Customer | None:
        result = await self._session.get(CustomerORM, customer_id)
        return self._to_domain(result) if result else None
```

### Domain ↔ ORM Dönüşümü

Repository, iki farklı model arasında **çeviri** yapar:

```
Domain Model (Customer)          ORM Model (CustomerORM)
──────────────────────          ──────────────────────
phone_number: PhoneNumber  ←→   phone_number: str
segment: CustomerSegment   ←→   segment: str
address: Address           ←→   address: dict (JSONB)
```

```python
# Domain → ORM
def _to_orm_dict(self, customer):
    return {
        "phone_number": customer.phone_number.full_number,  # ValueObject → str
        "segment": customer.segment.value,                  # Enum → str
        "address": customer.address.model_dump() if customer.address else None,
    }

# ORM → Domain
def _to_domain(self, orm):
    phone = PhoneNumber(number=orm.phone_number[3:])  # str → ValueObject
    return Customer(phone_number=phone, segment=CustomerSegment(orm.segment), ...)
```

---

## gRPC Proto Definitions

Servisler arası **internal** iletişim için gRPC tanımları hazırdır (REST dış istemciler içindir):

```protobuf
// infrastructure/grpc/customer.proto
service CustomerService {
  rpc GetCustomer(GetCustomerRequest) returns (CustomerResponse);
  rpc GetCustomersBySegment(GetBySegmentRequest) returns (CustomerListResponse);
  rpc GetCustomerProfile(GetCustomerRequest) returns (CustomerProfileResponse);
}
```

### CustomerProfileResponse

```protobuf
message CustomerProfileResponse {
  CustomerResponse customer = 1;
  int32 complaint_count = 2;
  int32 months_active = 3;
  double churn_risk_score = 4;
  repeated string recent_complaints = 5;  // son şikayetler
}
```

**Neden gRPC tanımı var ama server yok?** Proto dosyaları ilerideki fazlar için **kontrat** niteliğinde hazırlanmıştır. Servisler arası iletişim, dış istemcilere kıyasla daha düşük latency gerektirir ve Protobuf binary serialization bunu sağlar.

---

# PHASE 3 — CustomerSupportAgent

---

## Phase 3 — Büyük Resim

Phase 3'ün amacı platformun **ilk otonom AI agent'ını** oluşturmaktır: **CustomerSupportAgent**. Bu agent, müşteri şikayetlerini otomatik olarak alır, analiz eder, ticket oluşturur ve müşteriyi bilgilendirir.

### Ne Üretildi?

```
agents/customer_support/
├── agent.py             ← LangGraph ReAct agent + DeepSeek LLM
├── tools.py             ← 4 tool: profil, fatura, ticket, bildirim
├── memory.py            ← Redis short-term memory
├── kafka_consumer.py    ← Kafka'dan şikayet eventleri dinleme
├── metrics.py           ← Prometheus counter/histogram/gauge
├── main.py              ← FastAPI giriş noktası (/health, /complaint, /metrics)
├── Dockerfile           ← Container image
└── __init__.py
```

### Temel Felsefe

Agent, "**Event → Analiz → Aksiyon → Gözlemlenebilirlik**" döngüsünde çalışır:

```
Kafka Event ──→ Agent (LLM düşünür) ──→ Tool çağrıları ──→ Prometheus kaydı
                      ↑                       │
                      └── Redis memory ←───────┘
```

---

## LangGraph ReAct Pattern Nedir?

**ReAct**, "**Re**asoning + **Act**ing" kelimelerinin birleşimidir. LLM'in sadece metin üretmek yerine, **düşünüp → tool çağırıp → sonucu okuyup → tekrar düşünmesini** sağlayan bir agentic pattern'dir.

### Nasıl Çalışır?

```
┌─────────────────────────────────────────────────────┐
│                   LangGraph Agent                    │
│                                                      │
│  1. 📩 Mesaj gelir (şikayet)                         │
│  2. 🧠 LLM düşünür: "Önce müşteri profilini çekeyim"│
│  3. 🔧 Tool çağrısı: get_customer_profile(id)       │
│  4. 📄 Tool sonucu: {name: "Ali", segment: "gold"}  │
│  5. 🧠 LLM tekrar düşünür: "Şimdi faturayı çekeyim"│
│  6. 🔧 Tool çağrısı: get_billing_info(id)           │
│  7. 📄 Tool sonucu: [fatura listesi]                 │
│  8. 🧠 LLM analiz eder + çözüm oluşturur           │
│  9. 🔧 create_ticket + send_notification             │
│  10. ✅ Final yanıt döner                            │
└─────────────────────────────────────────────────────┘
```

### Projede Nasıl Implement Edildi?

```python
# agent.py — Sadece 3 satırda agent oluşturuluyor
agent = create_react_agent(
    model=llm,          # DeepSeek (OpenAI-compatible API)
    tools=ALL_TOOLS,    # 4 tool listesi
    prompt=SYSTEM_PROMPT # Türkçe kuralları olan system prompt
)
```

**Neden `create_react_agent`?**
- LangGraph'ın hazır ReAct implementasyonu
- Tool çağrılarını otomatik yönetir (hangi tool'u ne zaman çağıracağına LLM karar verir)
- Birden fazla döngü yapabilir (ilk tool sonucu yetersizse başka tool dener)

**Neden DeepSeek?**
- OpenAI API formatıyla uyumlu (`langchain-openai` paketi direkt çalışır)
- Düşük maliyet, yeterli kalite
- `temperature=0.1` → tutarlı, tekrarlanabilir yanıtlar

---

## Agent'ın Tool Sistemi

Agent'ın kullanabileceği 4 tool tanımlıdır. Her tool bir `@tool` decorator'ü ile LangChain'e kaydedilir ve agent runtime'da bunlardan seçim yapar.

### Tool'lar Tablosu

| # | Tool | Amacı | Veri Kaynağı |
|---|------|-------|-------------|
| 1 | `get_customer_profile` | Müşteri bilgilerini çeker (segment, CLV, plan) | Customer Service API |
| 2 | `get_billing_info` | Fatura geçmişini çeker | Billing Service API |
| 3 | `create_ticket` | Destek ticket'ı oluşturur | Lokal (production'da Ticket Service) |
| 4 | `send_notification` | Müşteriye SMS/email gönderir | Lokal (production'da Gateway) |

### Mock Fallback Mekanizması

Her tool'da aynı pattern uygulanmış: servis kapalıysa (`ConnectError`), mock data döner.

```python
@tool
async def get_customer_profile(customer_id: str) -> str:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{CUSTOMER_SERVICE_URL}/{customer_id}")
            resp.raise_for_status()
            return json.dumps(resp.json(), indent=2)
        except httpx.ConnectError:
            # ⬇️ Servis kapalıyken mock data döner
            return json.dumps({
                "id": customer_id,
                "name": "Demo Müşteri",
                "segment": "gold",
                "_mock": True,   # mock olduğunu belirten flag
            })
```

**Neden?** Geliştirme sırasında tüm servisleri ayağa kaldırmak zorunda kalmadan agent'ı test edebilmek için.

### Annotated Type Pattern

Tool parametrelerinde `Annotated` kullanılarak LLM'e parametre açıklamaları verilir:

```python
customer_id: Annotated[str, "UUID of the customer"]
category: Annotated[str, "Ticket category: billing | network | service | general"]
```

Bu sayede LLM, her parametreye ne göndereceğini tool tanımından öğrenir.

---

## Redis Short-Term Memory

Agent, her konuşma için bir **session** açar ve konuşma geçmişini Redis'te tutar.

### Key Schema

```
agent:session:{session_id}:messages   → liste (konuşma mesajları)
agent:session:{session_id}:metadata   → hash  (müşteri_id, şikayet tipi, öncelik)
```

### TTL (Time-To-Live) = 1 Saat

Session verileri 1 saat sonra otomatik silinir. Memory baskısını azaltır ve eski oturumların birikimini önler.

### Neden MongoDB Değil de Redis?

| Bellek Tipi | Store | Amaç | TTL |
|------------|-------|------|-----|
| Short-term | Redis | Aktif konuşma bağlamı | 1 saat |
| Long-term (gelecek) | MongoDB | Geçmiş deneyimler, öğrenme | Kalıcı |

---

## Kafka Consumer — Event-Driven Agent Tetikleme

Agent'ı 2 şekilde tetikleyebilirsin:

1. **Kafka üzerinden** (production yolu) — `telco.customers.complaints` topic'ine event yayınlanır
2. **REST API üzerinden** (test yolu) — `POST /v1/agent/complaint` endpoint'ine istek atılır

### Kafka Consumer Akışı

```
telco.customers.complaints topic
           │
           ▼
   ComplaintConsumer.start()
           │
           ▼
   _handle_message(raw_bytes)
           │
     ┌─────┴─────┐
     │ Deserialize│  ← JSON parse, başarısızsa DLQ'ya gönder
     └─────┬─────┘
           │
     ┌─────┴─────┐
     │  Validate  │  ← Pydantic schema kontrolü
     └─────┬─────┘
           │
     ┌─────┴──────────────┐
     │ agent.handle_complaint │  ← Agent'ı tetikle
     └─────┬──────────────┘
           │
     Başarısızsa → DLQ (Dead Letter Queue)
```

### Dead Letter Queue (DLQ) Nedir?

İşlenemeyen mesajları bir kenara ayıran "çöp" topic'i. 3 durumda DLQ'ya gönderilir:

| Durum | DLQ Payload |
|-------|------------|
| JSON parse hatası | `{"error": "deserialization_failed"}` |
| Schema validation hatası | `{"error": "validation_failed", "details": [...]}` |
| Agent işleme hatası | `{"error": "processing_failed", "event": {...}}` |

### Lifespan Pattern (FastAPI)

Kafka consumer, FastAPI'nin `lifespan` mekanizması ile arka planda başlatılır:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    consumer_task = asyncio.create_task(consumer.start())  # arka planda başla
    yield
    await consumer.stop()  # kapanırken durdur
```

---

## Prometheus Metrikleri — Observability

### Metrik Türleri

| Metrik | Tip | Ne Ölçer? |
|--------|-----|-----------|
| `agent_invocations_total` | **Counter** | Toplam agent çağrısı |
| `agent_latency_seconds` | **Histogram** | Uçtan uca süre (1s-120s bucket'ları) |
| `agent_tool_calls_total` | **Counter** | Hangi tool kaç kez çağrıldı |
| `agent_token_usage_total` | **Counter** | Prompt + completion token sayıları |
| `agent_errors_total` | **Counter** | Hata türlerine göre sayaç |
| `agent_active_sessions` | **Gauge** | Anlık aktif oturum sayısı |

### Counter vs Histogram vs Gauge

```
Counter   → Sadece artar. "Toplam kaç kez X oldu?"
Histogram → Değerlerin dağılımını ölçer. "Latency'nin %95'i kaç saniye?"
Gauge     → Artıp azalabilir. "Şu an kaç aktif session var?"
```

### Context Manager Pattern

```python
with self._metrics.track_invocation(complaint_type, priority):
    result = await self._agent.ainvoke(...)
```

Bu pattern otomatik olarak: girişte counter +1, çıkışta latency kaydı, exception'da error counter +1 yapar.

---

## Agent Akışı: Uçtan Uca Senaryo

### Senaryo: "Faturamda fazla ücret var" şikayeti

```
1. Customer Service'e yeni şikayet gelir
   └─→ Outbox pattern ile Kafka'ya ComplaintFiled event yayınlanır
          topic: telco.customers.complaints

2. ComplaintConsumer event'i okur → Pydantic validate → agent çağırır

3. Agent session oluşturur → Redis'e metadata yazar

4. LLM düşünür → get_customer_profile() çağırır
   → Sonuç: Gold segment, CLV 85, aktif

5. LLM düşünür → get_billing_info() çağırır
   → Sonuç: Ocak 245₺, Şubat 189₺

6. LLM analiz eder: "Gold segment → 4 saat SLA"

7. create_ticket() → send_notification()

8. Prometheus metrikleri kaydedilir
   Redis'e final yanıt yazılır
```

---

# PHASE 4 — MCP Layer

---

## Phase 4 — Büyük Resim

Phase 4'ün amacı **MCP (Model Context Protocol)** katmanını ekleyerek agent'ların tool'ları **statik kod yerine runtime'da dinamik olarak keşfetmesini** sağlamaktır.

### Ne Üretildi?

```
infrastructure/mcp/
├── customer_mcp_server.py   ← Customer domain: 5 tool + 2 resource
├── billing_mcp_server.py    ← Billing domain: 5 tool + 2 resource
├── client.py                ← Dynamic tool discovery + LangGraph wrapping
├── openapi_to_mcp.py        ← OpenAPI spec → MCP server code generator
└── __init__.py
```

### Temel Problem

Phase 3'te tool'lar **hardcode** edilmişti. Yeni tool = kod değiştir + restart.

Phase 4 çözümü: MCP server'lara yeni tool eklenir, agent runtime'da keşfeder. **Restart gerekmez.**

---

## MCP (Model Context Protocol) Nedir?

MCP, AI agent'ların dış dünyayla etkileşim kurması için standartlaştırılmış bir protokoldür.

### Temel Kavramlar

| Tür | Amacı | Örnekler |
|-----|-------|----------|
| **Tool** | Aksiyon alma (write) | `create_ticket`, `file_complaint` |
| **Resource** | Veri okuma (read-only) | `customer://segments`, `billing://currencies` |
| **Prompt** | Hazır prompt template'leri | (Bu projede kullanılmadı) |

---

## MCP Server'lar: Tool vs Resource

### Customer Domain MCP Server

| Tool | Neden? |
|------|--------|
| `get_customer_profile` | Müşteri profili çekme |
| `list_customers` | Segment bazlı müşteri listeleme |
| `get_customer_complaints` | Şikayet geçmişini listeleme |
| `file_complaint` | Yeni şikayet oluşturma (Kafka event tetikler) |
| `change_customer_segment` | Segment upgrade/downgrade |

| Resource (URI) | İçerik |
|-----|--------|
| `customer://segments` | new, bronze, silver, gold, platinum tanımları |
| `customer://complaint-types` | billing, network, service, general tanımları |

### Billing Domain MCP Server

| Tool | Neden? |
|------|--------|
| `get_invoices` | Müşteri fatura listesi |
| `get_invoice_detail` | Detaylı fatura (alt kalemler dahil) |
| `open_dispute` | Fatura itirazı açma |
| `calculate_billing_anomaly` | Anomali tespiti (%30+ sapma kontrolü) |
| `create_invoice` | Yeni fatura oluşturma |

### `calculate_billing_anomaly` — Detaylı Bakış

```python
avg = sum(amounts[1:]) / len(amounts[1:])  # geçmiş ortalaması
latest = amounts[0]                         # son fatura
deviation_pct = ((latest - avg) / avg) * 100
anomaly_detected = abs(deviation_pct) > 30  # %30'dan fazlaysa anomali
```

---

## MCP Client — Dynamic Tool Discovery

### 5 Adımlık Keşif Süreci

```
1. MCP_SERVER_REGISTRY'den server modüllerini oku
2. Her modülü import et, içindeki `mcp` objesini bul
3. Tool dict'ini çıkar (_tool_manager._tools)
4. inspect.signature() + pydantic.create_model() ile schema oluştur
5. StructuredTool wrapper ile LangGraph'a uyumlu hale getir
```

### Server Registry

```python
MCP_SERVER_REGISTRY = {
    "customer": "infrastructure.mcp.customer_mcp_server",
    "billing":  "infrastructure.mcp.billing_mcp_server",
    # Gelecekte tek satır ekleme:
    # "network":  "infrastructure.mcp.network_mcp_server",
}
```

### Agent Entegrasyonu

```python
# Statik tool'larla (Phase 3 yolu):
runner = CustomerSupportAgentRunner(use_mcp=False)  # → 4 hardcoded tool

# MCP ile dynamic discovery (Phase 4 yolu):
runner = CustomerSupportAgentRunner(use_mcp=True)   # → 12+ dynamic tool
```

---

## OpenAPI → MCP Auto-Generator

Yeni endpoint'ler için MCP tool tanımını otomatik üretir:

```bash
python -m infrastructure.mcp.openapi_to_mcp \
  --url http://localhost:8001/openapi.json \
  --output generated_tools.py
```

### Dönüşüm Kuralları

| OpenAPI | MCP Karşılığı |
|---------|---------------|
| Endpoint path + method | `@mcp.tool()` fonksiyonu |
| Path parametreleri | `Annotated[type, "description"]` |
| Request body fields | Fonksiyon parametreleri |
| Response | `json.dumps(resp.json())` |

---

## REST vs gRPC vs MCP Karşılaştırma

| Özellik | REST | gRPC | MCP |
|---------|------|------|-----|
| Serializasyon | JSON | Protobuf (binary) | JSON |
| Schema | Opsiyonel (OpenAPI) | Zorunlu (`.proto`) | Otomatik keşif |
| Hız | Orta | Hızlı | Orta |
| Agent Uyumluluğu | Manuel | Manuel | **Native** |
| Debug | Kolay (curl) | Zor | Orta |

**Ana çıkarım:** MCP'nin avantajı hız değil, **agent-native** olmasıdır — runtime discovery, no-restart.

---

# GENEL

---

## Tüm Fazların Birlikte Çalışması

```
Phase 1                    Phase 2                    Phase 3                    Phase 4
──────────────            ──────────────             ──────────────             ──────────────
Docker Compose    →       Customer Service   →       CustomerSupportAgent  →   MCP Servers
DDD Base Classes  →       Billing Service    →       Kafka Consumer        →   Dynamic Discovery
Settings          →       CQRS Handlers      →       Redis Memory          →   OpenAPI Codegen
Outbox DB Schema  →       Outbox → Kafka     →       Prometheus Metrics

                          ComplaintFiled     ───→     Agent tetiklenir     ←── MCP tool'ları
                          event (Kafka)                                        runtime'da keşfeder
```

### End-to-End Akış (4 Faz Birlikte)

```
1. [Phase 1] Docker Compose ile altyapı ayağa kalkar

2. [Phase 2] Customer Service'e REST API ile şikayet gelir
   → Customer.file_complaint() → ComplaintFiled event → Outbox tablosuna yazar
   → Outbox Poller → Kafka'ya "telco.customers.complaints" topic'ine gönderir

3. [Phase 3] Agent'ın Kafka Consumer'ı event'i okur
   → Agent LLM ile düşünür → Tool'lar aracılığıyla veri çeker
   → Ticket oluşturur, bildirim gönderir
   → Prometheus metrikleri kaydeder, Redis'e session yazar

4. [Phase 4] Agent use_mcp=True ise tool'ları MCP server'lardan keşfeder
   → Yeni tool eklemek = MCP server'a ekleme, agent restart gereksiz
```

---

## Scripts — Seed Data & Benchmark

### Mock Data Seeder (`scripts/seed_mock_data.py`)

Faker kütüphanesi ile **Türkçe** sahte veri üretir:

```python
fake = Faker("tr_TR")  # Türk isimleri, adresleri, telefon numaraları

# 50 müşteri, CLV segment'e göre ağırlıklı
# 150 fatura (her müşteriye 3 ay), Türkçe kalem açıklamaları
# ~15 şikayet (%30 müşteri), Türkçe şikayet metinleri
# 20 network node (base_station, fiber_node, switch, router)
```

**Kullanım:** `python scripts/seed_mock_data.py` — şu an sadece veri üretip ekrana yazdırır, DB entegrasyonu gelecek fazlarda.

### Protocol Benchmark (`scripts/benchmark_protocols.py`)

REST vs MCP vs gRPC performans karşılaştırması yapar:

```python
# 50 iterasyon, p50/p95/p99 latency hesaplaması
results = await asyncio.gather(
    benchmark_rest(customer_id, iterations=50),
    benchmark_mcp(customer_id, iterations=50),
    benchmark_grpc(customer_id, iterations=50),   # simulated
)
print_results(results)
```

**Sonuç formatı:** Tablo olarak avg, p50, p95, p99, min, max (ms) değerleri. gRPC henüz simüle edilir (server yok).

---

## Unit Tests — Test Altyapısı

`tests/` dizini 8 test dosyası ve `conftest.py` fixture dosyası içerir:

| Test Dosyası | Ne Test Eder? |
|-------------|---------------|
| `test_base_models.py` | ValueObject, Entity, AggregateRoot, DomainEvent |
| `test_customer_aggregate.py` | Customer.create(), change_segment(), file_complaint() |
| `test_customer_services.py` | CustomerSegmentationService, churn risk hesaplama |
| `test_invoice_aggregate.py` | Invoice lifecycle (create→pay, dispute→resolve) |
| `test_billing_value_objects.py` | Money aritmetiği, BillingPeriod, enum'lar |
| `test_billing_services.py` | BillingAnomalyService, %30 eşik testi |
| `test_agent_metrics.py` | Prometheus metrik doğruluğu |

**Test felsefesi:** Tüm testler **pure unit test** — dış altyapıya (DB, Kafka, Redis) bağımlılık yok. Mock'lar `conftest.py`'de tanımlı.

Çalıştırma:
```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

---

## Anahtar Mimari Kararlar Özet Tablosu

| Karar | Faz | Neden? |
|-------|-----|--------|
| **Docker Compose + ZooKeeper** | 1 | Tek komutla ayağa kalk, Kafka endüstri standardı kurulum |
| **DDD base class'lar (shared)** | 1 | Tüm domain'ler aynı yapı taşlarını kullanır |
| **Pydantic Settings** | 1 | Tip güvenli, .env destekli, singleton |
| **Katmanlı mimari (4 layer)** | 2 | Separation of concerns, domain sıfır altyapı bağımlılığı |
| **Factory Method** | 2 | Aggregate oluşturma + event yayınlama atomik |
| **CQRS** | 2 | Okuma/yazma ayrı optimize edilebilir |
| **Outbox Pattern** | 2 | DB + Kafka atomik tutarlılık |
| **Repository Pattern (abstract)** | 2 | Domain'i altyapıdan izole eder |
| **LangGraph ReAct** | 3 | LLM otonom düşünüp-hareket eder |
| **DeepSeek API** | 3 | Düşük maliyet, OpenAI-compatible |
| **Redis short-term memory** | 3 | Hızlı, TTL destekli, konuşma context'i |
| **Kafka consumer + DLQ** | 3 | Event-driven tetikleme, hatalı mesaj izolasyonu |
| **Prometheus context manager** | 3 | Latency tracking temiz, exception-safe |
| **FastMCP** | 4 | Dekoratör tabanlı, async native MCP server |
| **Dynamic tool discovery** | 4 | Restart gereksiz, yeni tool = registry ekleme |
| **OpenAPI codegen** | 4 | Manuel MCP tool yazımını ortadan kaldırır |
| **Tool/Resource ayrımı** | 4 | Write (tool) vs read-only (resource) semantiği |
| **Türkçe system prompt** | 3 | Domain-specific SLA kuralları, empatik iletişim |
| **5 dakika timeout** | 3 | Agent sonsuz döngüye girmez |
| **Mock fallback** | 3,4 | Servisler kapalıyken de test edilebilir |
| **init-db.sql + schema isolation** | 1 | Her bounded context kendi DB schema'sında |
| **Connection pool (10+20)** | 1 | Async session yönetimi, overflow limiti |
| **pgvector embedding kolonu** | 2 | Gelecekte similarity search için hazırlık |
| **Money (Decimal + operator)** | 2 | Float hassasiyet sorunu yok, currency invariant |
| **gRPC proto tanımları** | 1 | Servisler arası düşük latency, binary serialization |
| **Faker TR seed data** | 2 | Gerçekçi Türkçe test verisi üretimi |
| **Benchmark script** | 4 | REST/MCP/gRPC latency karşılaştırma kanıtı |

---

> **Sonuç:** Phase 1 altyapıyı ve DDD yapı taşlarını kurdu. Phase 2 bunların üzerine iş mantığını (Customer, Billing) inşa etti. Phase 3, platformun ilk otonom AI agent'ını oluşturdu — event-driven tetikleme, tool-based aksiyon alma, memory ve observability ile birlikte. Phase 4, bu agent'ın tool'larını **dinamik ve genişletilebilir** hale getirdi — MCP protokolü sayesinde yeni domain'ler eklemek artık konfigürasyon meselesi, kod değişikliği değil.
