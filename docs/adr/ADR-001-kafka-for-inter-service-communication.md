# ADR-001: Kafka Selected for Inter-Service Communication

## Status
Accepted — 2026-02-27

## Context
4 microservices (Customer, Network, Billing, Campaign) need to react to each other's domain events. Synchronous REST calls between services create temporal coupling and cascade failures.

Options considered:
1. **RabbitMQ** — Simple, AMQP, good for task queues
2. **Apache Kafka** — Event streaming, log-based, partitioning, consumer groups
3. **Direct REST/gRPC** — Synchronous, simple but tightly coupled

## Decision
All domain events will be published via Apache Kafka with Avro serialization and Schema Registry.
Synchronous communication is reserved only for gRPC calls that require immediate query results.

## Consequences
- Services can scale independently
- Consumers are unaffected if the producer service goes down
- Event replay capability for debugging and reprocessing
- Eventual consistency — no immediate data consistency
- Harder to debug — distributed tracing (Jaeger) is mandatory
- Schema Registry adds operational overhead but prevents breaking changes
