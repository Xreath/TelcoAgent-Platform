# ADR-006: Keycloak OAuth2.0 for API Security

**Status:** Accepted
**Date:** 2026-03-09
**Decision Makers:** Fazlı Koç

## Context

All FastAPI endpoints were initially public (no authentication). The platform needs proper API security with role-based access control.

## Decision

Use **Keycloak as OAuth2.0/OIDC provider** with JWT token validation in FastAPI middleware.

## Implementation

- Keycloak realm: `telco-agents` (already configured in Phase 1)
- 3 realm roles: `agent-operator`, `agent-supervisor`, `agent-auditor`
- 5 service clients (Client Credentials flow for service-to-service)
- 1 public client (`admin-ui`) for user-facing Password Grant
- FastAPI dependency: `get_current_user` validates JWT via JWKS endpoint
- Role enforcement: `require_role("agent-supervisor")` dependency factory
- JWKS cache: 5-minute TTL to avoid hammering Keycloak

## Access Control Matrix

| Endpoint | Required Role |
|----------|--------------|
| GET (read) endpoints | Any authenticated user |
| POST/PATCH (write) endpoints | agent-operator |
| Segment change, admin operations | agent-supervisor |
| Health check, metrics | No auth (public) |

## Consequences

- **Positive:** Enterprise-standard auth, role-based access, token-based stateless auth
- **Negative:** Keycloak dependency for all API calls, JWKS fetch latency on cold start
- **Mitigation:** JWKS cached for 5 minutes, stale cache used if Keycloak is temporarily unreachable
