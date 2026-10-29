# 10. Technology Stack Rationale & ADRs

## 10.1 Primary Technology Stack Summary

| Layer | Recommended Choice | Rationale | Alternatives Considered |
| :--- | :--- | :--- | :--- |
| **Edge Gateway Runtime** | **Go (Golang)** | Low memory footprint, compiled binary, native cross-compilation for ARM/x86, high concurrent protocol handling. | Rust (steeper learning curve), C++ (memory safety risks), Python (high memory/CPU overhead). |
| **Backend Microservices** | **Go + Java Spring Boot** | Go for throughput-critical services (ingestion, protocol handling); Java Spring for complex domain logic (ISO workflows). | Node.js (single-threaded limitations), Python (GIL performance bottleneck for microservices). |
| **Analytics & ML Engine** | **Python 3.11+** | Rich scientific ecosystem (PyTorch, XGBoost, Scikit-learn, Pandas, SHAP, Prophet, MILP solvers). | Julia (smaller ecosystem/community), C++ (slower iteration for ML). |
| **Frontend Framework** | **React 18 + TypeScript** | Rich visualization library ecosystem (Recharts, Apache ECharts), component modularity, strong typing. | Vue 3 (good, but smaller enterprise component ecosystem), Angular (opinionated overhead). |
| **Event Streaming** | **Apache Kafka / Redpanda** | Proven horizontal scale, exact-once processing semantics, replayable time-series stream. | RabbitMQ (weaker replayability), NATS JetStream (lighter, but smaller analytical integration ecosystem). |
| **Time-Series Database** | **TimescaleDB** | Full SQL compatibility, automatic time hypertable chunking, hybrid relational/time-series joins. | InfluxDB (Flux/InfluxQL learning curve, limited relational joins), Cassandra (high maintenance overhead). |
| **Relational Database** | **PostgreSQL 16** | Native `ltree` for graph trees, JSONB for flexible tagging, robust RLS for multi-tenancy. | MySQL (weaker indexing for tree/graph queries), MongoDB (lacks strong transactional consistency for audit logs). |
| **Identity & IAM** | **Keycloak** | Open-source enterprise IAM, native OIDC/SAML2, multi-tenant realm isolation. | Auth0 / Okta (high SaaS cost per identity at scale). |

---

## 10.2 Architecture Decision Records (ADRs)

### ADR-001: Time-Series Database Selection — TimescaleDB vs. InfluxDB
- **Status**: Decided
- **Context**: VerdantOS requires storage for millions of telemetry data points per day while enabling seamless SQL joins between time-series data and relational metadata (e.g., joining 15-minute power readings with asset metadata, tenant RLS policies, and EnPI baseline coefficients).
- **Decision**: Standardize on **TimescaleDB** (PostgreSQL extension).
- **Consequences**:
  - *Positive*: Unifies relational data and time-series data under PostgreSQL syntax; supports native multi-tenant RLS policies; continuous aggregates simplify rollups.
  - *Negative*: Higher storage footprint compared to custom column-compressed TSDBs, mitigated by enabling TimescaleDB columnar compression.

### ADR-002: Edge Gateway Runtime Language — Go vs. Python
- **Status**: Decided
- **Context**: The edge gateway must run reliably on resource-constrained industrial Linux PCs (down to 1 GB RAM ARM devices) and handle multithreaded polling across dozens of RS485 and Ethernet industrial meters.
- **Decision**: Select **Go (Golang)**.
- **Consequences**:
  - *Positive*: Single statically linked binary without external runtime dependencies; low footprint (< 50MB RAM usage); high concurrency via goroutines.
  - *Negative*: Lack of direct Python ML library execution on edge, requiring light CGO/ONNX C-bindings for on-edge anomaly inference.
