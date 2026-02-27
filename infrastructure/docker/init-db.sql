-- ============================================================
-- TelcoAgent Platform — Database Initialization
-- ============================================================
-- This script runs once when PostgreSQL container starts.
-- Creates separate schemas for each bounded context + extensions.
-- ============================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";          -- pgvector

-- Bounded Context schemas
CREATE SCHEMA IF NOT EXISTS customer;
CREATE SCHEMA IF NOT EXISTS network;
CREATE SCHEMA IF NOT EXISTS billing;
CREATE SCHEMA IF NOT EXISTS campaign;

-- Outbox schema (shared pattern)
CREATE SCHEMA IF NOT EXISTS outbox;

-- Keycloak schema
CREATE SCHEMA IF NOT EXISTS keycloak;

-- Temporal needs its own databases (auto-setup handles this)
-- But we ensure the schema exists for shared usage
CREATE SCHEMA IF NOT EXISTS temporal_visibility;

-- ============================================================
-- Outbox table (used by all domain services)
-- ============================================================
CREATE TABLE IF NOT EXISTS outbox.events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aggregate_type  VARCHAR(255) NOT NULL,
    aggregate_id    VARCHAR(255) NOT NULL,
    event_type      VARCHAR(255) NOT NULL,
    payload         JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at    TIMESTAMPTZ,
    published       BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_outbox_unpublished
    ON outbox.events (created_at)
    WHERE published = FALSE;
