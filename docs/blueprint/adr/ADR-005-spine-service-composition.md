# ADR-005: Architectural Spine Service Composition and Tenant-Context Mapping

## Status
Accepted

## Date
2026-10-20

## Decision Owner
Principal Software Architect

## Context
Phase 3 requires an explicit Architectural Spine composed of 6 minimal services to enable end-to-end platform deployment without feature pre-emption.

### Spine Service Mapping & Trade-offs (B-1 Resolution)
1. **`services/ingestion`** (`verdantos-svc-ingestion`): Protocol ingestion and store-and-forward edge upload receiver (`AC-01b`).
2. **`services/semantic-graph`** (`verdantos-svc-semantic-graph`): Asset tree hierarchy, ltree path queries, and Brick/Haystack tags (`AC-01b`).
3. **`services/enpi-engine`** (`verdantos-svc-enpi-engine`): EnPI formula DSL evaluator and MLR baseline engine (`AC-07a`).
4. **`services/anomaly-stream`** (`verdantos-svc-anomaly-stream`): *Skeleton deployment only*. Exposes `/healthz`, `/metrics`, and trace propagation. Tri-state decision logic (R-08) is dormant until Phase 4.
5. **`services/audit-service`** (`verdantos-svc-audit`): Immutable SHA-256 cryptographic ledger writer (`AC-11b`).
6. **`services/api-gateway`** (`verdantos-api-gateway`): Kong API Gateway + Tenant-Context Propagation Middleware.
   - *Tenant Context Propagation*: Keycloak validates OIDC JWT tokens, extracts `tenant_id` claim, and injects `X-Tenant-ID` header and OpenTelemetry trace span attributes across all downstream requests.

## Decision
Standardize the 6 spine services and map Kong API Gateway middleware as the tenant-context provider.

## Consequences
- *Positive*: Clear separation between platform infrastructure and domain microservices; zero Phase 4 logic leakage in Phase 3.
- *Negative*: Gateway middleware must strip incoming client-supplied `X-Tenant-ID` headers to prevent spoofing.
