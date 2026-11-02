# ADR-007: Data Connector Runtime Placement, Credential Management & Read-Only Governance

## Status
Accepted

## Context
VerdantOS requires extensible, high-throughput data connectors (§10.2) to ingest industrial telemetry, facility metadata, and utility invoices from external relational databases (PostgreSQL, MySQL, SQL Server, Oracle), local embedded databases (SQLite), and tabular file stores (.xlsx, .csv, .tsv). 

Connecting to external industrial databases introduces security, availability, and data integrity risks across trust boundaries:
1. Operational disruption of customer SCADA/historian/relational databases due to unconstrained query load or accidental write mutations.
2. Compromise of source credentials stored in cleartext or across multi-tenant contexts.
3. Network topology mismatches where edge gateways cannot reach cloud resources or cloud cannot reach on-premise industrial VLANs.
4. Duplicate telemetry ingestion or silent data loss across reconnects and partial failures.

## Decisions

### 1. Runtime Placement per Connector Type
- **Relational Database Connectors (PostgreSQL, MySQL, SQL Server, Oracle)**: Hybrid deployable (`edge` and `cloud`). When source databases reside in on-premise air-gapped or OT VLANs (Purdue Model Level 2/3), connectors execute within `verdantos-edge-standard` and `verdantos-edge-full` edge gateway containers. When cloud-hosted (e.g. AWS RDS, Azure SQL), connectors run in the central `service-connectors` spine container.
- **Embedded Database (SQLite)**: Executes strictly on `edge` profiles (`minimal`, `standard`, `full`) for local store-and-forward queue extraction.
- **Tabular Files (.xlsx, .csv, .tsv)**: Cloud-first within `service-connectors` for manual uploads via Web UI and S3/SharePoint automated pollers; edge-capable via local directory watcher on `verdantos-edge-standard`.

### 2. Credential Management & Multi-Tenant Secret Scope (ADR-Gap-1)
- **Pluggable Secrets Interface**: Connectors resolve `secret_ref` URIs through a unified `SecretProvider` interface:
  ```python
  class SecretProvider(ABC):
      @abstractmethod
      def get_secret(self, tenant_id: str, secret_key: str) -> Dict[str, Any]:
          pass
  ```
- **Three Reference Implementations**:
  - **Cloud (AWS)**: `AWSSecretsManagerProvider` resolving ARN pointers.
  - **Cloud (Multi-Cloud / Private Cloud)**: `VaultSecretProvider` resolving HashiCorp Vault KV v2 paths.
  - **Air-Gap Deployment (W11 Mode A)**: `LocalEncryptedSecretProvider` utilizing AES-256-GCM local storage with master keys derived via USB key ceremony (offline physical USB key token containing 256-bit entropy injected during site commissioning).
- **Residual Risk Statement**: `LocalEncryptedSecretProvider` protects secrets from unprivileged local OS users and network eavesdropping. It does not protect against an attacker possessing physical root/kernel-level access to the air-gap host hardware. This is an accepted and documented residual risk for air-gap deployments.
- **Scope & Isolation**: Strictly scoped per-tenant and per-source (`secret_ref = "vault://tenants/{tenant_id}/sources/{source_id}"`). Zero plaintext credentials in database columns, zero credentials in logs, zero credentials in environment files.

### 3. Provable Read-Only Enforcement & Three-Layer Defense (ADR-Gap-4)
To provide mathematical and driver-level guarantees that VerdantOS will NEVER mutate customer data:
- **Layer 1 (Session Characteristics)**: On socket connection, enforce `SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;` and `SET default_transaction_read_only = on;`.
- **Layer 2 (AST Query Inspection)**: Driver parses all SQL statements prior to dispatch; any statement other than `SELECT` (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `EXEC`) is rejected immediately with structured `SOURCE_READ_ONLY_VIOLATION`.
- **Layer 3 (Database Role Privilege Restriction)**: Customer database credentials must be provisioned with SELECT-only grants (`GRANT SELECT ON ... TO verdantos_reader;`). Connectors assert `has_table_privilege(current_user, table, 'INSERT') = false` during connection handshake.
- **Mandatory Negative Enforcement Test**: `test_connector_readonly_enforcement_blocks_writes` asserts that an explicit `INSERT` raises `SOURCE_READ_ONLY_VIOLATION`.

### 4. Mid-Chunk Failure Semantics & Watermark Advancement (ADR-Gap-2)
- **Chunk Transaction Model (Model A)**: Sync operates in atomic chunks of 1,000 rows (`BATCH_SIZE = 1,000`).
- **Semantics**:
  - Each 1,000-row chunk commits or rolls back as a single atomic unit.
  - On partial failure (e.g. failure at row 500 of a chunk), the entire 1,000-row chunk rolls back.
  - `sync_watermarks.watermark_sequence` advances strictly to the last committed chunk boundary (e.g., row 1,000).
  - Failure details and `last_failed_row` are recorded in `connector_runs` without advancing the persistent watermark.
  - Test `test_connector_watermark_rollback_on_chunk_failure` asserts watermark invariance on partial failure.

### 5. Rate Limiting, Backoff & Exhaustion Policy (ADR-Gap-3)
- **Configuration**:
  - `max_qps`: Default 10 queries/sec.
  - `initial_delay`: 1.0 second.
  - `backoff_factor`: 2.0.
  - `max_retries`: 5 attempts.
  - `max_total_delay`: 60.0 seconds.
- **Exhaustion Policy**: If the source database continues throttling after 5 retries, the run terminates with `SOURCE_RATE_LIMITED`. The watermark remains at the last successfully committed chunk boundary, and synchronization is deferred to the next scheduled interval.

### 6. Connector API Surface & OpenAPI Contract (ADR-Gap-5)
Executable OpenAPI 3.0 contract published at `contracts/openapi/connectors.yaml` covering:
1. `POST /api/v1/connectors`: Register external data source.
2. `GET /api/v1/connectors`: List tenant data sources.
3. `GET /api/v1/connectors/{id}`: Detailed source status and health.
4. `POST /api/v1/connectors/{id}/sync`: Trigger sync run.
5. `GET /api/v1/connectors/{id}/runs`: Query sync execution history.
6. `POST /api/v1/connectors/{id}/preview`: Fetch 100-row preview with detected types (no commit).
7. `POST /api/v1/connectors/{id}/mappings`: Configure column-to-point mappings.
8. `GET /api/v1/connectors/{id}/runs/{run_id}/errors`: Query structured per-row DQ error list.

### 7. Run-Level Error Taxonomy
Extends the STORY-2.B taxonomy:
- `SOURCE_UNREACHABLE` (FATAL)
- `SOURCE_AUTH_FAILED` (FATAL)
- `SOURCE_READ_ONLY_VIOLATION` (FATAL)
- `SOURCE_SCHEMA_DRIFT` (ERROR)
- `SOURCE_RATE_LIMITED` (WARN)
- `SOURCE_READ_TIMEOUT` (ERROR)
- `MAPPING_MISSING` (ERROR)


### 8. Audit Ledger Architecture & Cryptographic Hash-Chain Integration (STORY-2.11)
- **Decision**: Single Unified SHA-256 Hash Chain (Architecture A). Connector execution events append directly to the platform's primary ISO 50001 audit ledger (`audit_trail` table and composite pack).
- **Alternatives Considered**: Separate independent connector audit ledger (rejected: requires parallel verification tooling and bifurcates external ISO 50001 audit evidence packs).
- **Chain Entry Content**: Each connector run produces an immutable ledger entry containing:
  - `entity_type: 'connector_run'`, `action_type: 'EXECUTE_SYNC'`
  - `rows_read`, `rows_committed`, `rows_rejected`
  - `error_summary_sha256`: SHA-256 digest of the detailed error summary JSONB, providing cryptographic proof of data quality rejections without bloating the chain.
  - `previous_hash` & `cryptographic_hash`: Strictly chaining to the prior audit block.
- **Consequences**: Chain length grows proportionally with connector run volume. At 1,000 runs/day x 100 tenants, the chain grows by 100,000 entries/day. Mitigations: (a) verification tools stream the chain rather than load it fully; (b) connector entries are excluded from the operator-facing composite pack (which shows policy/EnPI/actions), and are verified separately by the tamper-detection CLI; (c) archival tiering groups entries by month with a monthly root hash chained to the next month. This is acceptable for current volume; tier (c) is scheduled for Phase 6.

## Consequences
- Guaranteed zero customer write risk via 3-layer defense (session, AST, role).
- Air-gap and cloud deployments share identical `SecretProvider` interface.
- Atomic 1,000-row chunk rollbacks prevent partial state corruption across source retries.
