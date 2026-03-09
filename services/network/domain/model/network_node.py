"""Network Domain — Aggregate Root."""

from __future__ import annotations

from datetime import UTC, datetime

from services.network.domain.model.events import (
    NetworkFaultResolved,
    NetworkNodeCreated,
    NetworkNodeStatusChanged,
)
from services.network.domain.model.value_objects import (
    Location,
    NodeStatus,
    NodeType,
)
from shared.models.base import AggregateRoot


class NetworkNode(AggregateRoot):
    """NetworkNode Aggregate Root — the consistency boundary for network infrastructure."""

    hostname: str
    node_type: NodeType
    status: NodeStatus = NodeStatus.ACTIVE
    location: Location
    ip_address: str | None = None
    firmware_version: str | None = None

    @classmethod
    def create(
        cls,
        hostname: str,
        node_type: NodeType,
        location: Location,
        ip_address: str | None = None,
        firmware_version: str | None = None,
    ) -> NetworkNode:
        """Factory method — creates a network node and raises NetworkNodeCreated event."""
        node = cls(
            hostname=hostname,
            node_type=node_type,
            location=location,
            ip_address=ip_address,
            firmware_version=firmware_version,
        )
        node.add_event(
            NetworkNodeCreated(
                aggregate_id=str(node.id),
                node_type=node_type.value,
                region=location.region,
            )
        )
        return node

    def change_status(self, new_status: NodeStatus, reason: str) -> None:
        """Change node operational status and raise domain event."""
        if new_status == self.status:
            return

        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.now(UTC)

        self.add_event(
            NetworkNodeStatusChanged(
                aggregate_id=str(self.id),
                old_status=old_status.value,
                new_status=new_status.value,
                reason=reason,
            )
        )

        # If transitioning back to active from a fault state, also raise resolved event
        if new_status == NodeStatus.ACTIVE and old_status in (NodeStatus.DEGRADED, NodeStatus.DOWN):
            self.add_event(
                NetworkFaultResolved(
                    aggregate_id=str(self.id),
                    previous_status=old_status.value,
                    resolution_note=reason,
                )
            )

    def mark_degraded(self, reason: str) -> None:
        """Convenience method — mark node as degraded."""
        self.change_status(NodeStatus.DEGRADED, reason)

    def mark_down(self, reason: str) -> None:
        """Convenience method — mark node as down."""
        self.change_status(NodeStatus.DOWN, reason)

    def restore(self, reason: str) -> None:
        """Convenience method — restore node to active."""
        self.change_status(NodeStatus.ACTIVE, reason)
