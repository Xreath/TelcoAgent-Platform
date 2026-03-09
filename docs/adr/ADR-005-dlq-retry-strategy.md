# ADR-005: DLQ with Exponential Backoff Retry Strategy

**Status:** Accepted
**Date:** 2026-03-09
**Decision Makers:** Fazlı Koç

## Context

Kafka consumers processing agent events can fail due to transient errors (LLM API timeout, service unavailable). Initial implementation sent failed messages directly to DLQ on first failure — no retry.

## Decision

Implement **in-process retry with exponential backoff** before dead-lettering.

## Strategy

| Error Type | Retryable? | Action |
|-----------|-----------|--------|
| Deserialization error | No | DLQ immediately |
| Validation error | No | DLQ immediately |
| Processing error (LLM timeout, service down) | Yes | Retry 3x with backoff, then DLQ |

**Backoff formula:** `delay = base_delay * 2^(attempt-1)`, capped at `max_delay`
- Default: base=2s, max=30s → delays: 2s, 4s, 8s

## Implementation

- Shared `RetryHandler` in `shared/kafka/retry.py` — used by both consumers
- `RetryConfig` dataclass: max_retries, base_delay, max_delay, dlq_topic
- DLQ messages enriched with: attempt count, first failure timestamp, last error, source topic

## Alternatives Considered

1. **Kafka retry topics** (e.g., `telco.retry.complaints.1`, `.2`, `.3`) — more robust but adds Kafka topic management complexity
2. **External retry service** (e.g., Temporal) — overkill for this use case
3. **Consumer seek-back** — risky, can cause message reprocessing storms

## Consequences

- **Positive:** Transient failures recovered automatically, DLQ only gets truly failed messages
- **Negative:** In-process retry blocks the consumer during backoff (acceptable with single-partition dev setup)
- **Future:** For production scale, migrate to Kafka retry topics with separate consumer groups
