"""Customer Service — SQLAlchemy ORM models (infrastructure layer)."""

import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.utils.database import Base


class CustomerORM(Base):
    __tablename__ = "customers"
    __table_args__ = {"schema": "customer"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    segment: Mapped[str] = mapped_column(String(50), nullable=False, default="new")
    subscription_plan: Mapped[str] = mapped_column(String(100), nullable=False, default="prepaid_basic")
    clv_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Address stored as JSONB (no separate table — value object)
    address: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # pgvector — customer profile embedding (for similarity search)
    profile_embedding: Mapped[list | None] = mapped_column(Vector(1536), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class ComplaintORM(Base):
    __tablename__ = "complaints"
    __table_args__ = {"schema": "customer"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    complaint_type: Mapped[str] = mapped_column(String(50), nullable=False)  # billing, network, service, general
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open")  # open, in_progress, resolved
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
