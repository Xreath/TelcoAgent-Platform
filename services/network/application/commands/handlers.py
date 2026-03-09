"""Network Service — Command Handlers (CQRS write side)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from services.network.domain.model.network_node import NetworkNode
from services.network.domain.model.value_objects import Location, NodeStatus, NodeType
from services.network.domain.services import AnomalyDetectionService, NodeMetrics
from services.network.infrastructure.kafka_publisher import OutboxRepository
from services.network.infrastructure.postgres_repository import PostgresNetworkNodeRepository


@dataclass
class CreateNodeCommand:
    hostname: str
    node_type: str  # bts | switch | router | core
    lat: float
    lng: float
    region: str
    ip_address: str | None = None
    firmware_version: str | None = None


@dataclass
class UpdateNodeStatusCommand:
    node_id: str
    new_status: str  # active | degraded | down
    reason: str


@dataclass
class DiagnoseNodeCommand:
    node_id: str


class NetworkCommandHandlers:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PostgresNetworkNodeRepository(session)
        self._outbox = OutboxRepository(session)

    async def handle_create_node(self, cmd: CreateNodeCommand) -> NetworkNode:
        """Create a new network node — saves to DB + writes events to outbox."""
        location = Location(lat=cmd.lat, lng=cmd.lng, region=cmd.region)
        node_type = NodeType(cmd.node_type)

        node = NetworkNode.create(
            hostname=cmd.hostname,
            node_type=node_type,
            location=location,
            ip_address=cmd.ip_address,
            firmware_version=cmd.firmware_version,
        )

        await self._repo.save(node)

        for event in node.collect_events():
            await self._outbox.save(event)

        return node

    async def handle_update_status(self, cmd: UpdateNodeStatusCommand) -> None:
        """Update node status — triggers NetworkNodeStatusChanged domain event."""
        import uuid

        node = await self._repo.find_by_id(uuid.UUID(cmd.node_id))
        if not node:
            raise ValueError(f"NetworkNode {cmd.node_id} not found")

        node.change_status(
            new_status=NodeStatus(cmd.new_status),
            reason=cmd.reason,
        )

        await self._repo.save(node)

        for event in node.collect_events():
            await self._outbox.save(event)

    async def handle_diagnose(self, cmd: DiagnoseNodeCommand) -> dict[str, object]:
        """Run diagnostic on a node — generates mock metrics and runs anomaly detection.

        Returns diagnostic results including metrics and any detected anomalies.
        """
        import random
        import uuid

        node = await self._repo.find_by_id(uuid.UUID(cmd.node_id))
        if not node:
            raise ValueError(f"NetworkNode {cmd.node_id} not found")

        # Generate mock metrics (in production these would come from monitoring infra)
        metrics = NodeMetrics(
            latency_ms=round(random.uniform(5.0, 500.0), 2),
            packet_loss_pct=round(random.uniform(0.0, 10.0), 2),
            throughput_mbps=round(random.uniform(5.0, 200.0), 2),
            uptime_pct=round(random.uniform(90.0, 100.0), 2),
        )

        # Run anomaly detection
        anomalies = AnomalyDetectionService.detect_anomalies(node, metrics)

        # Publish anomaly events to outbox
        for anomaly_event in anomalies:
            node.add_event(anomaly_event)

        # Check capacity threshold
        capacity_event = AnomalyDetectionService.check_capacity_threshold(node, metrics.throughput_mbps)
        if capacity_event:
            node.add_event(capacity_event)

        for event in node.collect_events():
            await self._outbox.save(event)

        return {
            "node_id": str(node.id),
            "hostname": node.hostname,
            "status": node.status.value,
            "metrics": {
                "latency_ms": metrics.latency_ms,
                "packet_loss_pct": metrics.packet_loss_pct,
                "throughput_mbps": metrics.throughput_mbps,
                "uptime_pct": metrics.uptime_pct,
            },
            "anomalies_detected": len(anomalies),
            "anomalies": [
                {
                    "metric": a.metric_name,
                    "value": a.metric_value,
                    "threshold": a.threshold,
                    "severity": a.severity,
                }
                for a in anomalies
            ],
            "capacity_warning": capacity_event is not None,
        }
