"""Network Domain — Domain Services (pure business logic, no infrastructure)."""

from __future__ import annotations

from dataclasses import dataclass

from services.network.domain.model.events import (
    CapacityThresholdReached,
    NetworkAnomalyDetected,
)
from services.network.domain.model.network_node import NetworkNode


@dataclass(frozen=True)
class NodeMetrics:
    """Snapshot of network node metrics for anomaly analysis."""

    latency_ms: float
    packet_loss_pct: float
    throughput_mbps: float
    uptime_pct: float


class AnomalyDetectionService:
    """Threshold-based anomaly detection on network node metrics.

    Pure domain logic — no external dependencies. Checks each metric against
    predefined thresholds and returns domain events for any anomalies found.
    """

    # Warning / critical thresholds
    LATENCY_WARNING_MS: float = 100.0
    LATENCY_CRITICAL_MS: float = 300.0

    PACKET_LOSS_WARNING_PCT: float = 1.0
    PACKET_LOSS_CRITICAL_PCT: float = 5.0

    THROUGHPUT_MIN_MBPS: float = 50.0  # capacity threshold

    @staticmethod
    def detect_anomalies(node: NetworkNode, metrics: NodeMetrics) -> list[NetworkAnomalyDetected]:
        """Analyze metrics and return anomaly events for any threshold violations."""
        anomalies: list[NetworkAnomalyDetected] = []

        # Latency check
        if metrics.latency_ms >= AnomalyDetectionService.LATENCY_CRITICAL_MS:
            anomalies.append(
                NetworkAnomalyDetected(
                    aggregate_id=str(node.id),
                    metric_name="latency_ms",
                    metric_value=metrics.latency_ms,
                    threshold=AnomalyDetectionService.LATENCY_CRITICAL_MS,
                    severity="critical",
                )
            )
        elif metrics.latency_ms >= AnomalyDetectionService.LATENCY_WARNING_MS:
            anomalies.append(
                NetworkAnomalyDetected(
                    aggregate_id=str(node.id),
                    metric_name="latency_ms",
                    metric_value=metrics.latency_ms,
                    threshold=AnomalyDetectionService.LATENCY_WARNING_MS,
                    severity="warning",
                )
            )

        # Packet loss check
        if metrics.packet_loss_pct >= AnomalyDetectionService.PACKET_LOSS_CRITICAL_PCT:
            anomalies.append(
                NetworkAnomalyDetected(
                    aggregate_id=str(node.id),
                    metric_name="packet_loss_pct",
                    metric_value=metrics.packet_loss_pct,
                    threshold=AnomalyDetectionService.PACKET_LOSS_CRITICAL_PCT,
                    severity="critical",
                )
            )
        elif metrics.packet_loss_pct >= AnomalyDetectionService.PACKET_LOSS_WARNING_PCT:
            anomalies.append(
                NetworkAnomalyDetected(
                    aggregate_id=str(node.id),
                    metric_name="packet_loss_pct",
                    metric_value=metrics.packet_loss_pct,
                    threshold=AnomalyDetectionService.PACKET_LOSS_WARNING_PCT,
                    severity="warning",
                )
            )

        # Throughput / capacity check
        if metrics.throughput_mbps < AnomalyDetectionService.THROUGHPUT_MIN_MBPS:
            anomalies.append(
                NetworkAnomalyDetected(
                    aggregate_id=str(node.id),
                    metric_name="throughput_mbps",
                    metric_value=metrics.throughput_mbps,
                    threshold=AnomalyDetectionService.THROUGHPUT_MIN_MBPS,
                    severity="critical" if metrics.throughput_mbps < 10.0 else "warning",
                )
            )

        return anomalies

    @staticmethod
    def check_capacity_threshold(
        node: NetworkNode, current_throughput_mbps: float, threshold_mbps: float = 50.0
    ) -> CapacityThresholdReached | None:
        """Check if a node's throughput has dropped below the capacity threshold."""
        if current_throughput_mbps < threshold_mbps:
            return CapacityThresholdReached(
                aggregate_id=str(node.id),
                current_throughput_mbps=current_throughput_mbps,
                threshold_mbps=threshold_mbps,
                region=node.location.region,
            )
        return None
