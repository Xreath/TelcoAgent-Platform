# Phase 4: MCP Layer — Tamamlandı

**Tarih:** 2026-03-02

## Oluşturulan Dosyalar

| Dosya | İçerik |
|-------|--------|
| `infrastructure/mcp/__init__.py` | Package init |
| `infrastructure/mcp/customer_mcp_server.py` | Customer domain MCP server — 5 tool + 2 resource |
| `infrastructure/mcp/billing_mcp_server.py` | Billing domain MCP server — 5 tool + 2 resource |
| `infrastructure/mcp/client.py` | `MCPToolClient` — dynamic tool discovery, LangGraph uyumlu wrapping |
| `infrastructure/mcp/openapi_to_mcp.py` | CLI: OpenAPI spec → FastMCP kodu otomatik üretim |
| `scripts/benchmark_protocols.py` | REST vs gRPC vs MCP latency karşılaştırma |

## Güncellenen Dosyalar

| Dosya | Değişiklik |
|-------|-----------|
| `agents/customer_support/agent.py` | `use_mcp=True` mode eklendi — MCP tool'ları runtime'da keşfeder |

## Customer Domain MCP Server

### Tool'lar
| Tool | Açıklama |
|------|----------|
| `get_customer_profile` | Müşteri profili (segment, plan, CLV, iletişim) |
| `list_customers` | Müşteri listesi, segment filtresi destekli |
| `get_customer_complaints` | Müşterinin şikayetleri (en yeni → en eski) |
| `file_complaint` | Yeni şikayet oluştur (Kafka event tetikler) |
| `change_customer_segment` | Segment değiştir (upgrade/downgrade) |

### Resource'lar
| URI | İçerik |
|-----|--------|
| `customer://segments` | Segment tanımları (new, bronze, silver, gold, platinum) |
| `customer://complaint-types` | Şikayet tipleri (billing, network, service, general) |

## Billing Domain MCP Server

### Tool'lar
| Tool | Açıklama |
|------|----------|
| `get_invoices` | Müşterinin fatura listesi |
| `get_invoice_detail` | Fatura detayı (kalemler dahil) |
| `open_dispute` | Fatura itirazı aç (BillingAnalystAgent tetikler) |
| `calculate_billing_anomaly` | Fatura geçmişinde anomali tespiti (%30+ sapma) |
| `create_invoice` | Yeni fatura oluştur |

### Resource'lar
| URI | İçerik |
|-----|--------|
| `billing://invoice-statuses` | Fatura durumları (pending, paid, overdue, disputed, cancelled, refunded) |
| `billing://currencies` | Desteklenen para birimleri (TRY, USD, EUR) |

## MCP Client — Dynamic Tool Discovery

**Dosya:** `infrastructure/mcp/client.py`

### Nasıl Çalışır
1. `MCPToolClient` MCP server modüllerini import eder
2. `FastMCP._tool_manager._tools` üzerinden tool'ları keşfeder
3. `inspect.signature()` ile parametre bilgisi çıkarır
4. `pydantic.create_model()` ile input schema oluşturur
5. `StructuredTool` wrapper ile LangGraph'a uyumlu hale getirir

### Kullanım
```python
from infrastructure.mcp.client import MCPToolClient

client = MCPToolClient()
tools = await client.discover_tools()
# tools artık LangGraph create_react_agent'a verilebilir
```

### Agent Entegrasyonu
```python
# Statik tool'larla (eski yol):
runner = CustomerSupportAgentRunner(use_mcp=False)

# MCP ile dynamic discovery (yeni yol):
runner = CustomerSupportAgentRunner(use_mcp=True)
# → MCP server'lara yeni tool eklendiğinde agent restart gerekmez
```

## OpenAPI → MCP Auto-Generator

**Dosya:** `infrastructure/mcp/openapi_to_mcp.py`

### CLI Kullanımı
```bash
# Çalışan bir FastAPI servisinden:
python -m infrastructure.mcp.openapi_to_mcp \
  --url http://localhost:8001/openapi.json \
  --output generated_customer_tools.py

# Lokal JSON dosyasından:
python -m infrastructure.mcp.openapi_to_mcp \
  --file openapi.json \
  --output tools.py
```

### Ne Üretir
- Her OpenAPI path+method için bir `@mcp.tool()` fonksiyonu
- Path/query parametreleri → `Annotated[type, "description"]`
- Request body → fonksiyon parametreleri
- Response → `json.dumps(resp.json())`

## REST vs gRPC vs MCP Benchmark

**Dosya:** `scripts/benchmark_protocols.py`

```bash
python scripts/benchmark_protocols.py
```

### Ölçülen Metrikler
- Avg, P50, P95, P99, Min, Max latency (ms)
- 50 iterasyon per protocol (3 warmup)

### Beklenen Sonuçlar
| Protocol | Avantaj | Dezavantaj |
|----------|---------|------------|
| REST | Basit, yaygın, debug kolay | Schema validation yok |
| gRPC | Hızlı (protobuf), type-safe | Karmaşık setup, debug zor |
| MCP | Dynamic discovery, agent-native | Schema overhead, henüz yeni |

## Mimari Kararlar

| Karar | Gerekçe |
|-------|---------|
| FastMCP (custom MCP değil) | Hızlı başlangıç, decorator-based, async native |
| Direct import mode (subprocess değil) | Aynı process'te çalışır, latency düşük, dev için ideal |
| Tool + Resource ayrımı | Tool = aksiyon (write), Resource = veri (read-only) |
| Mock fallback tüm tool'larda | Servisler kapalıyken de agent test edilebilir |
| OpenAPI codegen | Yeni endpoint eklendiğinde MCP tool tanımı otomatik üretilir |
| Server registry (dict) | Yeni MCP server eklemek = tek satır ekleme |

## MCP Server Registry

```python
# infrastructure/mcp/client.py
MCP_SERVER_REGISTRY = {
    "customer": "infrastructure.mcp.customer_mcp_server",
    "billing": "infrastructure.mcp.billing_mcp_server",
    # Phase 5'te eklenecek:
    # "network": "infrastructure.mcp.network_mcp_server",
    # "campaign": "infrastructure.mcp.campaign_mcp_server",
}
```
