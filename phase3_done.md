# Phase 3: CustomerSupportAgent — Tamamlandı

**Tarih:** 2026-03-02

## Oluşturulan Dosyalar

| Dosya | İçerik |
|-------|--------|
| `agents/customer_support/tools.py` | 4 tool: `get_customer_profile`, `get_billing_info`, `create_ticket`, `send_notification` — servisler kapalıyken mock fallback |
| `agents/customer_support/memory.py` | `RedisMemory` — session messages + metadata, TTL 1h, async Redis |
| `agents/customer_support/agent.py` | LangGraph `create_react_agent` + DeepSeek LLM + Türkçe system prompt + SLA kuralları |
| `agents/customer_support/kafka_consumer.py` | `telco.customers.complaints` topic'ten event consume → agent tetikleme |
| `agents/customer_support/metrics.py` | Prometheus: invocation count/latency, tool calls, token usage, active sessions |
| `agents/customer_support/main.py` | FastAPI: `/health`, `/v1/agent/complaint` (manual test), `/metrics` |
| `agents/customer_support/Dockerfile` | Python 3.11 slim container |
| `agents/customer_support/__init__.py` | Package init |

## Güncellenen Dosyalar

| Dosya | Değişiklik |
|-------|-----------|
| `docker-compose.yml` | `customer-support-agent` servis eklendi (port 8010, Traefik routing) |
| `infrastructure/monitoring/prometheus/prometheus.yml` | Agent scrape target eklendi |

## Mimari Kararlar

- **LangGraph ReAct** pattern — `create_react_agent(model, tools, prompt)`
- **DeepSeek API** (OpenAI-compatible) — düşük maliyet, `langchain-openai` ile direkt çalışır
- **Redis short-term memory** — key schema: `agent:session:{id}:messages` + `:metadata`, TTL 1h
- **Kafka consumer** — `aiokafka` async loop, FastAPI lifespan'da background task olarak çalışır
- **Mock fallback** — tool'larda servisler kapalıyken dev/test için mock data döner
- **Türkçe system prompt** — priority-based SLA kuralları (critical: 1h, high: 4h, medium: 24h, low: 48h)

## Agent Akışı

```
ComplaintFiled event (Kafka: telco.customers.complaints)
  → KafkaConsumer receives
    → Agent fetches customer profile + billing info (tools)
      → LLM analyzes complaint
        → Creates ticket + sends notification (tools)
          → Metrics recorded (Prometheus)
            → Conversation saved (Redis)
```

## Prometheus Metrikleri

| Metrik | Tip | Açıklama |
|--------|-----|----------|
| `agent_invocations_total` | Counter | Toplam agent çağrısı (label: complaint_type, priority) |
| `agent_latency_seconds` | Histogram | End-to-end latency (buckets: 1-120s) |
| `agent_tool_calls_total` | Counter | Tool çağrı sayısı (label: tool_name) |
| `agent_token_usage_total` | Counter | Token kullanımı (prompt/completion) |
| `agent_errors_total` | Counter | Hata sayısı (label: error_type) |
| `agent_active_sessions` | Gauge | Aktif session sayısı |

## Endpoint'ler (port 8010)

| Method | Path | Açıklama |
|--------|------|----------|
| GET | `/health` | Health check |
| POST | `/v1/agent/complaint` | Manuel agent tetikleme (test için) |
| GET | `/metrics` | Prometheus metrics |

## Test Komutu (manual)

```bash
curl -X POST http://localhost:8010/v1/agent/complaint \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "some-uuid",
    "complaint_type": "billing",
    "description": "Faturamda fazla ücret var",
    "priority": "high"
  }'
```
