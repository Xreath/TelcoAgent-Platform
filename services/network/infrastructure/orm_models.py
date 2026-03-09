"""Network Service — SQLAlchemy ORM models (infrastructure layer)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.utils.database import Base


class NetworkNodeORM(Base):
    __tablename__ = "network_nodes"
    __table_args__ = {"schema": "network"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hostname: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    node_type: Mapped[str] = mapped_column(String(50), nullable=False)  # bts, switch, router, core
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")

    # Location fields (flattened — value object stored as columns)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)

    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv4/IPv6
    firmware_version: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
