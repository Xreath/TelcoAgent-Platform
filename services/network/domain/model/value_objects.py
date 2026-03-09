"""Network Domain — Value Objects."""

from __future__ import annotations

from enum import StrEnum

from shared.models.base import ValueObject


class NodeStatus(StrEnum):
    """Operational status of a network node."""

    ACTIVE = "active"
    DEGRADED = "degraded"
    DOWN = "down"


class NodeType(StrEnum):
    """Type of network equipment."""

    BTS = "bts"
    SWITCH = "switch"
    ROUTER = "router"
    CORE = "core"


class Location(ValueObject):
    """Geographic location of a network node."""

    lat: float
    lng: float
    region: str
