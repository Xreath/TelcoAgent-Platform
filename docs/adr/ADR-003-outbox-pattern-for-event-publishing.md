# ADR-003: Outbox Pattern for Event Publishing

**Status:** Accepted
**Date:** 2026-02-27
**Decision Makers:** Fazlı Koç

## Context

Domain services need to publish events to Kafka when state changes occur (e.g., customer created, complaint filed, invoice disputed). The challenge is ensuring atomicity — the database write and Kafka publish must either both succeed or both fail.

## Options Considered

1. **Direct publish** — Publish to Kafka inside the request handler after DB commit
2. **Outbox Pattern** — Write event to an `outbox.events` table in the same DB transaction, then poll and publish
3. **CDC (Change Data Capture)** — Use Debezium to stream WAL changes to Kafka

## Decision

Use the **Outbox Pattern** with a polling-based publisher.

## Rationale

- **Atomic guarantee:** Event is persisted in the same transaction as business data — no dual-write problem
- **Simpler than CDC:** Debezium requires additional infrastructure (connector, WAL config) — overkill for a learning project
- **Reliable than direct publish:** If Kafka is down, events queue in the outbox and are published when Kafka recovers
- **Debuggable:** Events are visible in the database, can be replayed manually

## Implementation

- `outbox.events` table: id, aggregate_type, aggregate_id, event_type, payload (JSONB), published flag
- `OutboxPoller` runs every 5 seconds, fetches unpublished events, publishes to Kafka, marks as published
- Each bounded context has its own `OutboxRepository` + `OutboxPoller` instance
- Topic mapping is per-service (e.g., `customer.complaint_filed` → `telco.customers.complaints`)

## Consequences

- **Positive:** Zero message loss, simple implementation, works with any SQL database
- **Negative:** 5-second polling delay (acceptable for this use case), outbox table grows (needs periodic cleanup)
- **Trade-off:** At-least-once delivery — consumers must be idempotent
