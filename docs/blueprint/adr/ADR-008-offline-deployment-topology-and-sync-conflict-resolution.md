# ADR-008: Offline Deployment Topology & Sync Conflict Resolution Strategy

## Status
Accepted

## Context
VerdantOS serves two distinct disconnected operational models (§10.3 / Workstream 11):
1. **Mode A — Air-Gap Deployment**: Dedicated industrial sites with strict zero-internet regulatory mandates (critical infrastructure, nuclear, defense). The full platform spine, local PostgreSQL/TimescaleDB, Kafka, Redis, Keycloak, React web shell, and ML runtimes execute on single-node Docker Compose (≤50GB telemetry) or K3s clusters without external egress.
2. **Mode B — Edge Offline & Reconnect**: Distributed campus buildings and remote plants with cloud connectivity subject to transient or prolonged WAN partitions (e.g. 72-hour network loss). Edge gateways must maintain continuous local data acquisition, local EnPI calculation, CUSUM drift detection, action logging, and site-scoped UI, followed by zero-loss bidirectional reconciliation upon WAN reconnection.

## Decisions

### 1. Air-Gap Deployment Topology (Mode A)
- **Shared Codebase Guarantee**: Executes the identical database migrations (`V1`, `V2`, `V3`, `V4`), identical Go ingestion adapters, and identical Python analytics engines as cloud deployments.
- **Service Composition (16-Container Topology)**:
  | Container | Mode A Port | Mode A Role |
  |---|---|---|
  | postgres | 5432 (internal) | PostgreSQL 16 + TimescaleDB local time-series & relational store |
  | redis | 6379 (internal) | Local sliding-window cache & transient event buffer |
  | kafka | 9092 (internal) | Apache Kafka single-node event bus for canonical envelopes |
  | schema-registry | 8081 (internal) | Avro/JSON schema registry for event envelope validation |
  | keycloak | 8080 (internal) | Local OIDC authentication provider for air-gap operator accounts |
  | api-gateway | 8000 (exposed) | Kong API gateway with tenant context & route security |
  | service-ingestion | internal | Multi-protocol ingestion spine service |
  | service-semantic-graph | internal | Semantic asset model & hierarchy query spine service |
  | service-enpi-engine | internal | ISO 50006 EnPI computation spine service |
  | service-anomaly-stream | internal | Tri-state anomaly classifier & CUSUM drift detection spine service |
  | service-audit | internal | SHA-256 hash-chain audit logging spine service |
  | service-connectors | internal | Multi-source batch/incremental data connector spine service |
  | service-baseline-advisor | internal | Auto-baseline proposal and model selection spine service |
  | web-dashboard | 3000 (exposed) | React 18 local web shell for site operators & audit reviews |
  | edge-gateway-standard | internal | Local edge gateway adapter runtime with embedded TimescaleDB |
  | minio | 9000 (internal) | S3-compatible local object store for audit packs & report PDFs |
- **Ports & Boundaries**: Exposes internal ports 8000 (API Gateway), 3000 (UI), and 5432 (Postgres local admin). Cloud egress (`443`, `80`) is blocked and unrouted.

### 2. Edge TimescaleDB for Standard & Full Profiles
- **Profile Envelopes & Detailed RSS Budgets**:
  - `verdantos-edge-minimal` (50MB RAM limit): Retains lightweight SQLite store-and-forward buffer for low-spec IoT gateways.
  - `verdantos-edge-standard` (150MB RAM limit): Upgraded from SQLite to embedded single-node TimescaleDB.
  - `verdantos-edge-full` (300MB RAM limit): Upgraded from Badger to embedded TimescaleDB + local ONNX runtime.

Standard profile (150MB budget):
  TimescaleDB shared_buffers:  32MB
  TimescaleDB background:      ~25MB
  Edge gateway:                ~50MB
  OS page cache reservation:   ~15MB
  Query working memory:        ~28MB (reserved)
  Total:                       150MB

Full profile (300MB budget):
  TimescaleDB shared_buffers:  64MB
  TimescaleDB background:      ~35MB
  Edge gateway:                ~65MB
  Local ONNX runtime:          ~80MB
  OS page cache reservation:   ~25MB
  Query working memory:        ~31MB (reserved)
  Total:                       300MB

- **Constraint Enforcement**: Enforced at container level via Docker cgroup memory limits (`docker run --memory=150m`).

### 3. Sync Conflict Resolution Policy (LWW with Domain Precedence)
- **Telemetry Data (Edge Source-of-Truth)**:
  - **Edge Precedence**: The edge gateway holds direct physical telemetry from sensors. In any timestamp/point collision, edge telemetry takes precedence over cloud estimates.
  - **Conflict Key**: `(tenant_id, source_id, point_id, timestamp)`.
  - **Tiebreaker**: Last-Write-Wins (LWW) per `(point_id, timestamp)` with edge-always precedence.
- **Configuration & Semantic Models (Cloud Source-of-Truth)**:
  - **Cloud Precedence**: Asset hierarchy mutations, equipment templates, and baseline formula updates authored in cloud take precedence over edge state.
  - **Logging**: All configuration discrepancies are recorded into `sync_conflicts` table for operator review.

### 4. Offline Licensing Mechanism
- **Cryptographic Token**: Offline license is a self-contained, cryptographically signed JSON Web Token (JWT) using **Ed25519** asymmetric cryptography (256-bit security, high verification throughput).
- **Embedded Verification Key**: Public verification key embedded directly in platform binaries.
- **Claims Payload**:
  - `tenant_id`: Licensed tenant UUID.
  - `entitlements`: Enabled modules (`enms`, `bms`, `connectors`, `advisor`).
  - `max_points`: Metric point ceiling.
  - `expires_at`: Epoch expiry timestamp.
- **Grace Period & Failure Modes**:
  - 60-day read-only grace period after `expires_at`.
  - During grace, platform displays prominent regulatory audit warnings but continues EnPI calculation and data recording.
  - After grace, enters strict read-only mode (no new asset/telemetry writes; audit log export remains active).
  - Zero phone-home requirement. Renewals imported via signed license file over USB ceremony.
- **Consequence of Embedded Key Rotation**:
  Rotating the public verification key requires deploying a new platform binary release. In air-gap environments, customers must import an authorized update bundle via USB ceremony prior to license expiration under the new key.
  Mitigation: A 90-day overlap transition window is provided during key rollover wherein platform binaries support dual verification keys (current key and previous key), ensuring existing air-gap sites renew licenses seamlessly without forced immediate binary upgrades.

### 5. Signed Update Bundles & Key Separation
- **Cryptographic Key Decision**:
  Separate keys: VOS_LICENSE_SIGNING_KEY_v1 and VOS_RELEASE_SIGNING_KEY_v1.
- **Key Responsibilities**:
  - `VOS_LICENSE_SIGNING_KEY_v1` (Ed25519): Dedicated strictly to signing customer offline license JWTs.
  - `VOS_RELEASE_SIGNING_KEY_v1` (Ed25519): Dedicated strictly to signing air-gap release bundles (`.vos` archives).
  - Rationale: Isolates code execution trust from license commercial entitlements; compromise of a commercial license key cannot forge executable system updates.
- **Air-Gap Bundle Archive & Rollback**:
  - Update bundles are packaged as signed `.vos` archives (tar.zst) containing container images, Flyway append-only migrations, and a manifest digest.
  - Rollback Procedure: Migrations execute within an atomic transaction. If any migration fails, the transaction is rolled back completely, container image activation is aborted, previous binary versions remain active, and an audit failure record is logged to `audit_trail`.

### 6. Bidirectional Reconciliation Protocol & Partial-Sync Recovery
- **Standard Protocol Sequence**:
  1. Sequence Reconciliation: Edge transmits sequence range `[seq_start, seq_end]`.
  2. Chunked Resumable Ingestion: Telemetry streamed in 1,000-point chunks with ACK responses.
  3. Digest Verification: Edge and cloud calculate SHA-256 digest of payload for the acked sequence range:
     `digest = SHA256(seq_start | seq_end | point_count | sum(values))`. Matching digests seal the synchronization window.
- **Partial-Sync Disconnect Recovery**:
  If a network partition occurs mid-sync after chunks 1..N of M have been received, the cloud's `offline_sync_state.last_synced_sequence` reflects chunk N. Upon reconnection:
  - Edge queries cloud's `last_synced_sequence`.
  - Edge resumes transmission from sequence `N + 1`.
  - Post-completion digest is computed across the full sequence range `1..M` on both edge and cloud.
  - If digests match, the entire sync window is committed. If a digest mismatch is detected, the cloud re-requests the full sequence range from the edge (idempotent upsert), ensuring zero silent data corruption.

### 7. Self-Contained Compliance Profile
All compliance verification tools are 100% self-contained and run without network connectivity:
- `python tools/ci_validate_traceability.py`: Standalone regex linter (zero egress).
- `python tools/audit_verify.py`: Standalone SHA-256 hash-chain verifier (zero egress).
- `python tools/check_ddl_report_inventory.py`: Standalone DDL inventory checker (zero egress).

## Consequences
- Enables compliant ISO 50001 deployments in high-security air-gap environments.
- Edge TimescaleDB integration allows identical SQL query logic across edge and cloud.
- Reconnection digest checks guarantee zero data loss across multi-day WAN outages.

### 8. Edge Node Identifier Design
The `edge_node_id VARCHAR(64)` is designed as a free-form identifier (such as hardware UUID, serial number, or provisioning slug). A formal cloud registry table `edge_nodes` is planned under STORY-2.15a.
