# Architectural Spine Component Map

| Spine Component | Service / Container Name | Port | Owning Repo Path | Satisfied PLAN.md AC ID | Function & Platform Contract |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Semantic Asset Service** | `verdantos-svc-semantic-graph` | 8082 | `services/semantic-graph` | `AC-01b` | Asset hierarchy, ltree paths, Brick/Haystack tags. |
| **2. EnPI / Baseline Engine** | `verdantos-svc-enpi-engine` | 8083 | `services/enpi-engine` | `AC-07a` | EnPI formula DSL evaluator & CUSUM solver. |
| **3. Ingestion Pipeline** | `verdantos-svc-ingestion` | 8081 | `services/ingestion` | `AC-01b` | Telemetry ingestion & Protobuf envelope validation. |
| **4. Audit Log Writer** | `verdantos-svc-audit` | 8085 | `services/audit-service` | `AC-11b` | Cryptographic SHA-256 hash-chain ledger writer. |
| **5. Edge Gateway** | `verdantos-edge-standard` | 8088 | `edge/` | `AC-01b` | Protocol polling (BACnet/Modbus) & store-and-forward. |
| **6. API Gateway & Identity** | `verdantos-api-gateway` | 8000 | `services/api-gateway` | `AC-04a` | Kong Gateway + Keycloak OIDC Tenant-Context Middleware. |

*Note on `verdantos-svc-anomaly-stream`*: Deployed as a skeleton container exposing platform contract endpoints (`/healthz`, `/metrics`). R-08 tri-state ML logic is disabled until Phase 4.
