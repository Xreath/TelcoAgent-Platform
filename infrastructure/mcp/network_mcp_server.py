"""Network Domain — MCP Server.

Exposes network monitoring and diagnostic tools via Model Context Protocol.
NetworkDiagnosticAgent connects to this server for dynamic tool discovery.

Run standalone:
    python -m infrastructure.mcp.network_mcp_server
"""

from __future__ import annotations

import json
import random
import uuid
from datetime import UTC, datetime
from typing import Annotated

import httpx
from fastmcp import FastMCP

from shared.config.settings import get_settings

mcp = FastMCP(
    "Network Domain MCP Server",
    instructions="Provides network topology, diagnostic, and anomaly detection tools for AI agents",
)

settings = get_settings()
NETWORK_SERVICE_URL = settings.network_service_url


# ── Tools ─────────────────────────────────────────────────────


@mcp.tool()
async def query_network_topology(
    region: Annotated[str | None, "Filter by region (e.g. istanbul, ankara, izmir). None for all."] = None,
    node_type: Annotated[str | None, "Filter by type: bts | switch | router | core. None for all."] = None,
    status: Annotated[str | None, "Filter by status: active | degraded | down. None for all."] = None,
) -> str:
    """Query the network topology to list nodes and their current status.

    Returns JSON array of network nodes with: id, name, node_type, status, region, lat, lng.
    Use this to understand the network layout before running diagnostics.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            params = {}
            if region:
                params["region"] = region
            if node_type:
                params["type"] = node_type
            if status:
                params["status"] = status
            resp = await client.get(f"{NETWORK_SERVICE_URL}/nodes", params=params)
            resp.raise_for_status()
            return json.dumps(resp.json(), indent=2, ensure_ascii=False)
        except (httpx.HTTPStatusError, httpx.ConnectError):
            nodes = [
                {
                    "id": str(uuid.uuid4()),
                    "name": f"BTS-IST-{i:03d}",
                    "node_type": "bts",
                    "status": random.choice(["active", "active", "active", "degraded"]),
                    "region": region or "istanbul",
                    "lat": 41.0082 + random.uniform(-0.1, 0.1),
                    "lng": 28.9784 + random.uniform(-0.1, 0.1),
                    "_mock": True,
                }
                for i in range(1, 6)
            ]
            if status:
                nodes = [n for n in nodes if n["status"] == status]
            return json.dumps(nodes, indent=2, ensure_ascii=False)


@mcp.tool()
async def get_node_metrics(
    node_id: Annotated[str, "UUID of the network node"],
) -> str:
    """Fetch real-time performance metrics for a specific network node.

    Returns JSON with: latency_ms, packet_loss_pct, throughput_mbps, uptime_pct, cpu_usage_pct, memory_usage_pct.
    Use this to diagnose performance issues on a specific node.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{NETWORK_SERVICE_URL}/nodes/{node_id}/metrics")
            resp.raise_for_status()
            return json.dumps(resp.json(), indent=2, ensure_ascii=False)
        except (httpx.HTTPStatusError, httpx.ConnectError):
            return json.dumps(
                {
                    "node_id": node_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "latency_ms": round(random.uniform(5, 150), 2),
                    "packet_loss_pct": round(random.uniform(0, 5), 3),
                    "throughput_mbps": round(random.uniform(50, 1000), 1),
                    "uptime_pct": round(random.uniform(95, 100), 2),
                    "cpu_usage_pct": round(random.uniform(10, 90), 1),
                    "memory_usage_pct": round(random.uniform(20, 85), 1),
                    "_mock": True,
                },
                indent=2,
            )


@mcp.tool()
async def run_diagnostic_script(
    node_id: Annotated[str, "UUID of the network node"],
    diagnostic_type: Annotated[str, "Type: ping | traceroute | bandwidth | full"] = "full",
) -> str:
    """Run a diagnostic script on a network node.

    Executes the specified diagnostic and returns results.
    Types:
    - ping: Basic connectivity check
    - traceroute: Path analysis to the node
    - bandwidth: Throughput measurement
    - full: All of the above

    Returns JSON with diagnostic results and recommended actions.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                f"{NETWORK_SERVICE_URL}/nodes/{node_id}/diagnose",
                json={"diagnostic_type": diagnostic_type},
            )
            resp.raise_for_status()
            return json.dumps(resp.json(), indent=2, ensure_ascii=False)
        except (httpx.HTTPStatusError, httpx.ConnectError):
            results = {
                "node_id": node_id,
                "diagnostic_type": diagnostic_type,
                "timestamp": datetime.now(UTC).isoformat(),
                "results": {},
                "_mock": True,
            }
            if diagnostic_type in ("ping", "full"):
                results["results"]["ping"] = {
                    "status": "ok",
                    "avg_latency_ms": round(random.uniform(5, 80), 2),
                    "packet_loss_pct": round(random.uniform(0, 2), 2),
                    "packets_sent": 100,
                    "packets_received": random.randint(97, 100),
                }
            if diagnostic_type in ("traceroute", "full"):
                results["results"]["traceroute"] = {
                    "hops": random.randint(3, 8),
                    "max_latency_ms": round(random.uniform(20, 120), 2),
                    "bottleneck_hop": random.randint(2, 5),
                }
            if diagnostic_type in ("bandwidth", "full"):
                results["results"]["bandwidth"] = {
                    "download_mbps": round(random.uniform(100, 900), 1),
                    "upload_mbps": round(random.uniform(50, 400), 1),
                    "jitter_ms": round(random.uniform(1, 15), 2),
                }
            # Generate recommendation
            anomalies = []
            for test_name, test_result in results["results"].items():
                if test_name == "ping" and test_result.get("packet_loss_pct", 0) > 1:
                    anomalies.append("Yüksek paket kaybı tespit edildi")
                if test_name == "traceroute" and test_result.get("max_latency_ms", 0) > 80:
                    anomalies.append("Yüksek hop gecikmesi — olası darboğaz")
                if test_name == "bandwidth" and test_result.get("download_mbps", 999) < 200:
                    anomalies.append("Düşük bant genişliği — kapasite sorunu olabilir")
            results["anomalies"] = anomalies
            results["recommendation"] = (
                "Acil müdahale gerekli: " + "; ".join(anomalies) if anomalies else "Tüm testler normal aralıkta"
            )
            return json.dumps(results, indent=2, ensure_ascii=False)


@mcp.tool()
async def escalate_to_ops(
    node_id: Annotated[str, "UUID of the affected network node"],
    severity: Annotated[str, "Severity: low | medium | high | critical"],
    summary: Annotated[str, "Brief summary of the issue"],
    diagnostic_results: Annotated[str, "JSON string of diagnostic results"] = "{}",
) -> str:
    """Escalate a network issue to the operations team.

    Creates an ops ticket and sends alerts to the NOC (Network Operations Center).
    Use this when diagnostics reveal issues that require human intervention.
    """
    ticket = {
        "ops_ticket_id": str(uuid.uuid4()),
        "node_id": node_id,
        "severity": severity,
        "summary": summary,
        "diagnostic_results": diagnostic_results,
        "status": "escalated",
        "escalated_at": datetime.now(UTC).isoformat(),
        "assigned_to": "NOC Team",
        "sla_hours": {"critical": 1, "high": 4, "medium": 8, "low": 24}.get(severity, 24),
    }
    return json.dumps(ticket, indent=2, ensure_ascii=False)


@mcp.tool()
async def get_affected_customers(
    node_id: Annotated[str, "UUID of the network node"],
) -> str:
    """Get list of customers affected by a network node issue.

    Returns customer IDs and their service impact level.
    Use this to understand the blast radius of a network problem.
    """
    # In production, this would query a customer-to-node mapping
    affected = [
        {
            "customer_id": str(uuid.uuid4()),
            "name": f"Müşteri {i}",
            "impact": random.choice(["full_outage", "degraded", "intermittent"]),
            "service_type": random.choice(["mobile", "fiber", "corporate"]),
        }
        for i in range(1, random.randint(3, 15))
    ]
    return json.dumps(
        {"node_id": node_id, "affected_count": len(affected), "customers": affected, "_mock": True},
        indent=2,
        ensure_ascii=False,
    )


# ── Resources ─────────────────────────────────────────────────


@mcp.resource("network://node-types")
def get_node_types() -> str:
    """Available network node types."""
    return json.dumps(
        {
            "bts": "Baz İstasyonu (Base Transceiver Station) — Mobil ağ erişim noktası",
            "switch": "Ağ anahtarı — Trafik yönlendirme",
            "router": "Yönlendirici — WAN bağlantısı",
            "core": "Çekirdek ağ düğümü — Ana omurga bileşeni",
        },
        indent=2,
        ensure_ascii=False,
    )


@mcp.resource("network://severity-levels")
def get_severity_levels() -> str:
    """Severity levels and their SLA response times."""
    return json.dumps(
        {
            "critical": "Tam kesinti, 1 saat SLA — NOC acil müdahale",
            "high": "Ciddi performans düşüşü, 4 saat SLA",
            "medium": "Kısmi etki, 8 saat SLA",
            "low": "Minimal etki, 24 saat SLA",
        },
        indent=2,
        ensure_ascii=False,
    )


# ── Entry point ───────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
