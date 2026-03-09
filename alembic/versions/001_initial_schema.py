"""Initial schema — customer and billing bounded contexts.

Revision ID: 001
Revises: None
Create Date: 2026-03-09

Idempotent: tables already created via create_all are silently skipped.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _exists(bind: sa.engine.Connection, schema: str, table: str) -> bool:
    row = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema=:s AND table_name=:t"
        ),
        {"s": schema, "t": table},
    ).fetchone()
    return row is not None


def upgrade() -> None:
    bind = op.get_bind()

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE SCHEMA IF NOT EXISTS customer")
    op.execute("CREATE SCHEMA IF NOT EXISTS billing")

    # ── customer.customers ───────────────────────────────────
    if not _exists(bind, "customer", "customers"):
        op.create_table(
            "customers",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("phone_number", sa.String(20), nullable=False),
            sa.Column("email", sa.String(255), nullable=True),
            sa.Column("segment", sa.String(50), nullable=False, server_default="new"),
            sa.Column("subscription_plan", sa.String(100), nullable=False, server_default="prepaid_basic"),
            sa.Column("clv_score", sa.Float, nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
            sa.Column("address", postgresql.JSONB, nullable=True),
            sa.Column("profile_embedding", sa.Text, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.UniqueConstraint("phone_number", name="uq_customers_phone"),
            schema="customer",
        )
        op.execute("ALTER TABLE customer.customers DROP COLUMN IF EXISTS profile_embedding")
        op.execute("ALTER TABLE customer.customers ADD COLUMN IF NOT EXISTS profile_embedding vector(1536)")

    # ── customer.complaints ──────────────────────────────────
    if not _exists(bind, "customer", "complaints"):
        op.create_table(
            "complaints",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("complaint_type", sa.String(50), nullable=False),
            sa.Column("description", sa.Text, nullable=False),
            sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
            sa.Column("status", sa.String(50), nullable=False, server_default="open"),
            sa.Column("resolution", sa.Text, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["customer_id"], ["customer.customers.id"],
                name="fk_complaints_customer", ondelete="CASCADE",
            ),
            schema="customer",
        )
        op.create_index("ix_complaints_customer_id", "complaints", ["customer_id"], schema="customer")

    # ── billing.invoices ─────────────────────────────────────
    if not _exists(bind, "billing", "invoices"):
        op.create_table(
            "invoices",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("period_year", sa.Integer, nullable=False),
            sa.Column("period_month", sa.Integer, nullable=False),
            sa.Column("amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("currency", sa.String(10), nullable=False, server_default="TRY"),
            sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
            sa.Column("dispute_status", sa.String(50), nullable=True),
            sa.Column("line_items", postgresql.JSONB, nullable=False, server_default="[]"),
            sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            schema="billing",
        )
        op.create_index("ix_invoices_customer_id", "invoices", ["customer_id"], schema="billing")

    # ── billing.disputes ─────────────────────────────────────
    if not _exists(bind, "billing", "disputes"):
        op.create_table(
            "disputes",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("reason", sa.Text, nullable=False),
            sa.Column("status", sa.String(50), nullable=False, server_default="open"),
            sa.Column("resolution", sa.Text, nullable=True),
            sa.Column("refund_amount", sa.Numeric(12, 2), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["invoice_id"], ["billing.invoices.id"],
                name="fk_disputes_invoice", ondelete="CASCADE",
            ),
            schema="billing",
        )
        op.create_index("ix_disputes_invoice_id", "disputes", ["invoice_id"], schema="billing")
        op.create_index("ix_disputes_customer_id", "disputes", ["customer_id"], schema="billing")


def downgrade() -> None:
    op.drop_table("disputes", schema="billing")
    op.drop_table("invoices", schema="billing")
    op.drop_table("complaints", schema="customer")
    op.drop_table("customers", schema="customer")
    op.execute("DROP SCHEMA IF EXISTS billing")
    op.execute("DROP SCHEMA IF EXISTS customer")
