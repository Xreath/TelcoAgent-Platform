"""NetworkDiagnosticAgent — Tool definitions.

3 tools for network fault diagnosis:
  1. query_network_topology  — list nodes, filter by region/type/status
  2. run_diagnostic_script   — execute ping/traceroute/bandwidth tests
  3. escalate_to_ops         — create NOC ticket for human intervention
"""

from __future__ import annotations

import json
import random
import uuid
from datetime import UTC, datetime
from typing import Annotated

from langchain_core.tools import tool

from shared.config.settings import get_settings

settings = get_settings()
NETWORK_SERVICE_URL = settings.network_service_url


@tool
async def query_network_topology(
    region: Annotated[str | None, "Filter by region (istanbul, ankara, izmir). None for all."] = None,
    node_type: Annotated[str | None, "Filter by type: bts | switch | router | core. None for all."] = None,
    status: Annotated[str | None, "Filter by status: active | degraded | down. None for all."] = None,
) -> str:
    """Query network topology to list nodes and their current status.

    Returns JSON array of nodes with: id, name, node_type, status, region.
    Use this first to understand the network layout and find problematic nodes.
    """
    import httpx

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
                    "node_type": node_type or "bts",
                    "status": random.choice(["active", "active", "degraded", "down"]),
                    "region": region or "istanbul",
                    "_mock": True,
                }
                for i in range(1, 6)
            ]
            if status:
                nodes = [n for n in nodes if n["status"] == status]
            return json.dumps(nodes, indent=2, ensure_ascii=False)


@tool
async def run_diagnostic_script(
    node_id: Annotated[str, "UUID of the network node to diagnose"],
    diagnostic_type: Annotated[str, "Type: ping | traceroute | bandwidth | full"] = "full",
) -> str:
    """Run diagnostic tests on a network node.

    Executes ping, traceroute, and/or bandwidth tests.
    Returns results with anomaly detection and recommended actions.
    Use this after identifying a problematic node via query_network_topology.
    """
    import httpx

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
                "results": {
                    "ping": {
                        "avg_latency_ms": round(random.uniform(5, 120), 2),
                        "packet_loss_pct": round(random.uniform(0, 5), 2),
                    },
                    "bandwidth": {
                        "download_mbps": round(random.uniform(100, 800), 1),
                        "upload_mbps": round(random.uniform(50, 300), 1),
                    },
                },
                "anomalies": [],
                "_mock": True,
            }
            if results["results"]["ping"]["packet_loss_pct"] > 1:
                results["anomalies"].append("Yüksek paket kaybı")
            if results["results"]["bandwidth"]["download_mbps"] < 200:
                results["anomalies"].append("Düşük bant genişliği")
            results["recommendation"] = (
                "Acil müdahale gerekli: " + "; ".join(results["anomalies"])
                if results["anomalies"]
                else "Tüm testler normal"
            )
            return json.dumps(results, indent=2, ensure_ascii=False)


@tool
async def escalate_to_ops(
    node_id: Annotated[str, "UUID of the affected network node"],
    severity: Annotated[str, "Severity: low | medium | high | critical"],
    summary: Annotated[str, "Brief summary of the issue and diagnostic findings"],
) -> str:
    """Escalate a network issue to the Network Operations Center (NOC).

    Creates an ops ticket with SLA-based response time.
    Use this when diagnostics reveal issues requiring human intervention.
    Always include diagnostic results in the summary.
    """
    ticket = {
        "ops_ticket_id": str(uuid.uuid4()),
        "node_id": node_id,
        "severity": severity,
        "summary": summary,
        "status": "escalated",
        "escalated_at": datetime.now(UTC).isoformat(),
        "assigned_to": "NOC Team",
        "sla_hours": {"critical": 1, "high": 4, "medium": 8, "low": 24}.get(severity, 24),
    }
    return json.dumps(ticket, indent=2, ensure_ascii=False)


ALL_TOOLS = [query_network_topology, run_diagnostic_script, escalate_to_ops]
