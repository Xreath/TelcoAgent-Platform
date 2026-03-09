"""Network Domain — Domain Events."""

from __future__ import annotations

from shared.events.base import DomainEvent


class NetworkAnomalyDetected(DomainEvent):
    """Raised when anomaly detection identifies abnormal metrics on a node."""

    event_type: str = "network.anomaly_detected"
    aggregate_type: str = "NetworkNode"
    metric_name: str  # "latency_ms", "packet_loss_pct", "throughput_mbps"
    metric_value: float
    threshold: float
    severity: str  # "warning", "critical"


class NetworkFaultResolved(DomainEvent):
    """Raised when a network fault is resolved and the node returns to active."""

    event_type: str = "network.fault_resolved"
    aggregate_type: str = "NetworkNode"
    previous_status: str
    resolution_note: str


class CapacityThresholdReached(DomainEvent):
    """Raised when a node's throughput drops below the capacity threshold."""

    event_type: str = "network.capacity_threshold_reached"
    aggregate_type: str = "NetworkNode"
    current_throughput_mbps: float
    threshold_mbps: float
    region: str


class NetworkNodeCreated(DomainEvent):
    """Raised when a new network node is registered."""

    event_type: str = "network.node_created"
    aggregate_type: str = "NetworkNode"
    node_type: str
    region: str


class NetworkNodeStatusChanged(DomainEvent):
    """Raised when a node's operational status changes."""

    event_type: str = "network.node_status_changed"
    aggregate_type: str = "NetworkNode"
    old_status: str
    new_status: str
    reason: str
